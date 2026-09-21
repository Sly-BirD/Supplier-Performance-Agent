"""
Data Importer — parses tabular datasets, normalizes transactions,
computes scorecards, and triggers threshold alerts.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import (
    Supplier,
    DataSource,
    SourceType,
    TransactionRecord,
    Dimension,
    Alert as AlertModel,
    AlertRuleType,
    AlertSeverity,
)
from src.config.defaults import DEFAULT_SCORING_CONFIG, DEFAULT_ALERT_CONFIG
from src.config.store import ConfigStore
from src.engines.scoring_engine import ScoringEngine, CompositeScore, DimensionScore
from src.engines.alert_engine import AlertEngine
from src.services.email_service import send_alert_email, AlertEmailData, is_email_configured

logger = logging.getLogger(__name__)


def _parse_date(val: object) -> datetime:
    """Safely parse various date representations into timezone-aware datetime."""
    if val is None or pd.isna(val) or str(val).strip() == "":
        return datetime.now(timezone.utc)
    try:
        dt = pd.to_datetime(val)
        if dt.tzinfo is None:
            return dt.tz_localize("UTC").to_pydatetime()
        return dt.to_pydatetime()
    except Exception:
        return datetime.now(timezone.utc)


def _clean_num(val: object, default: float = 0.0) -> float:
    """Safely extract float from strings or numbers."""
    if val is None or pd.isna(val):
        return default
    try:
        s = str(val).replace("$", "").replace("%", "").replace(",", "").strip()
        return float(s)
    except Exception:
        return default


async def ingest_dataframe(
    df: pd.DataFrame,
    db: AsyncSession,
    source_name: str = "Uploaded Dataset",
    user_id: str = "dev-user",
) -> dict:
    """
    Ingest a DataFrame of supplier performance observations.

    Workflow:
    1. Register DataSource
    2. Identify or create Suppliers (scoped by user_id)
    3. Normalize and insert TransactionRecords
    4. Compute scorecards via ScoringEngine & persist ScoreSnapshots
    5. Evaluate AlertEngine rules & persist Alerts
    6. Commit transaction
    """
    if df.empty:
        return {"row_count": 0, "suppliers_count": 0, "alerts_fired": 0, "message": "Dataset is empty"}

    # 1. Register data source (scoped to user)
    data_source = DataSource(
        user_id=user_id,
        source_type=SourceType.CSV,
        filename=source_name,
        row_count=len(df),
    )
    db.add(data_source)
    await db.flush()

    # Map column names to lowercase stripped strings
    col_map = {col: str(col).strip().lower().replace(" ", "_").replace("-", "_") for col in df.columns}
    normalized_cols = {v: k for k, v in col_map.items()}

    # 2. Find supplier column
    sup_col_orig = None
    for cand in ["suppliername", "supplier_name", "supplier", "vendor_name", "vendorname", "vendor", "supplierid", "supplier_id", "vendor_id", "sup_id"]:
        if cand in normalized_cols:
            sup_col_orig = normalized_cols[cand]
            break

    if not sup_col_orig:
        # Fallback to the first object or string column
        for col in df.columns:
            if df[col].dtype == "object":
                sup_col_orig = col
                break

    if not sup_col_orig:
        sup_col_orig = df.columns[0]

    # Category column if available
    cat_col_orig = None
    for cand in ["category", "supplier_category", "type", "industry", "commodity"]:
        if cand in normalized_cols:
            cat_col_orig = normalized_cols[cand]
            break

    # Region column if available
    region_col_orig = None
    for cand in ["region", "country", "location", "geo"]:
        if cand in normalized_cols:
            region_col_orig = normalized_cols[cand]
            break

    # Identify date columns
    date_col = None
    for cand in ["date", "record_date", "shipdate", "ship_date", "duedate", "due_date", "inspection_date", "invoicedate", "invoice_date", "order_date"]:
        if cand in normalized_cols:
            date_col = normalized_cols[cand]
            break

    # Check if dates in dataset are historical and need calibration to active scoring window
    date_offset = timedelta(0)
    check_date_col = date_col or normalized_cols.get("shipdate") or normalized_cols.get("duedate")
    if check_date_col:
        try:
            parsed_dates = [_parse_date(val) for val in df[check_date_col].dropna()]
            if parsed_dates:
                max_dt = max(parsed_dates)
                now_utc = datetime.now(timezone.utc)
                if (now_utc - max_dt).days > 45:
                    # Shift records so newest record is 2 days ago
                    date_offset = (now_utc - timedelta(days=2)) - max_dt
        except Exception:
            pass

    # Check for direct score columns (summary datasets)
    deliv_sc_col = normalized_cols.get("delivery_score") or normalized_cols.get("deliveryscore") or normalized_cols.get("delivery")
    qual_sc_col = normalized_cols.get("quality_score") or normalized_cols.get("qualityscore") or normalized_cols.get("quality")
    cost_sc_col = (
        normalized_cols.get("cost_score")
        or normalized_cols.get("costscore")
        or normalized_cols.get("pricing_score")
        or normalized_cols.get("pricingscore")
        or normalized_cols.get("cost")
        or normalized_cols.get("pricing")
    )
    rel_sc_col = normalized_cols.get("reliability_score") or normalized_cols.get("reliabilityscore") or normalized_cols.get("reliability")
    comm_sc_col = normalized_cols.get("communication_score") or normalized_cols.get("communicationscore") or normalized_cols.get("communication")
    overall_sc_col = (
        normalized_cols.get("overall_score")
        or normalized_cols.get("overallscore")
        or normalized_cols.get("composite_score")
        or normalized_cols.get("compositescore")
        or normalized_cols.get("total_score")
        or normalized_cols.get("score")
    )
    risk_col = normalized_cols.get("risk_level") or normalized_cols.get("risklevel") or normalized_cols.get("risk")
    has_summary_scores = bool(overall_sc_col or (deliv_sc_col and qual_sc_col))

    direct_scores_by_supplier: dict[str, CompositeScore] = {}
    direct_alerts_to_create: list[AlertModel] = []

    # Cache existing suppliers (scoped to this user)
    existing_res = await db.execute(select(Supplier).where(Supplier.user_id == user_id))
    existing_suppliers = {s.name.lower().strip(): s for s in existing_res.scalars().all()}
    affected_suppliers: dict[str, Supplier] = {}

    transactions: list[TransactionRecord] = []

    # 3. Process each row
    for _, row in df.iterrows():
        raw_name = str(row.get(sup_col_orig, "")).strip()
        if not raw_name or raw_name.lower() in ["nan", "null", "none", ""]:
            continue

        sup_key = raw_name.lower()
        if sup_key in existing_suppliers:
            supplier = existing_suppliers[sup_key]
        else:
            category_val = str(row.get(cat_col_orig, "General")).strip() if cat_col_orig else "General"
            region_val = str(row.get(region_col_orig, "Global")).strip() if region_col_orig else "Global"
            supplier = Supplier(
                user_id=user_id,
                name=raw_name,
                category=category_val if category_val.lower() not in ["nan", "none"] else "General",
                region=region_val if region_val.lower() not in ["nan", "none"] else "Global",
            )
            db.add(supplier)
            await db.flush()
            existing_suppliers[sup_key] = supplier

        affected_suppliers[supplier.id] = supplier
        rec_date = (_parse_date(row.get(date_col)) + date_offset) if date_col else datetime.now(timezone.utc)

        # ─── Check Direct Score / Summary Columns ───
        if has_summary_scores:
            deliv = _clean_num(row.get(deliv_sc_col), 75.0) if deliv_sc_col else 75.0
            qual = _clean_num(row.get(qual_sc_col), 75.0) if qual_sc_col else 75.0
            cost = _clean_num(row.get(cost_sc_col), 75.0) if cost_sc_col else 75.0
            rel = _clean_num(row.get(rel_sc_col), 75.0) if rel_sc_col else 75.0
            comm = _clean_num(row.get(comm_sc_col), 80.0) if comm_sc_col else 80.0

            if overall_sc_col and pd.notna(row.get(overall_sc_col)):
                overall = _clean_num(row.get(overall_sc_col), 75.0)
            else:
                overall = round(deliv * 0.25 + qual * 0.25 + cost * 0.20 + rel * 0.15 + comm * 0.15, 1)

            risk_str = str(row.get(risk_col, "")).strip().lower() if risk_col else ""
            if "crit" in risk_str or overall < 65:
                tier = "Critical"
            elif "risk" in risk_str or "high" in risk_str or overall < 75:
                tier = "At-Risk"
            elif "med" in risk_str or "watch" in risk_str or overall < 85:
                tier = "Watch"
            elif overall >= 90:
                tier = "Preferred"
            else:
                tier = "Approved"

            if overall < 75 or "crit" in risk_str or "risk" in risk_str or "high" in risk_str:
                trend = "↓"
            elif overall >= 90:
                trend = "↑"
            else:
                trend = "flat"

            dim_scores = {
                Dimension.DELIVERY.value: DimensionScore(dimension=Dimension.DELIVERY, score=deliv),
                Dimension.QUALITY.value: DimensionScore(dimension=Dimension.QUALITY, score=qual),
                Dimension.PRICING.value: DimensionScore(dimension=Dimension.PRICING, score=cost),
                Dimension.RELIABILITY.value: DimensionScore(dimension=Dimension.RELIABILITY, score=rel),
                Dimension.COMMUNICATION.value: DimensionScore(dimension=Dimension.COMMUNICATION, score=comm),
            }

            direct_scores_by_supplier[supplier.id] = CompositeScore(
                score=overall,
                tier=tier,
                trend=trend,
                dimension_scores=dim_scores,
                prior_score=round(overall + (2.5 if trend == "↓" else (-2.0 if trend == "↑" else 0.0)), 1),
            )

            # Synthetic transactions for auditability
            for dim, metric_n, val in [
                (Dimension.DELIVERY, "delivery_score", deliv),
                (Dimension.QUALITY, "quality_score", qual),
                (Dimension.PRICING, "cost_score", cost),
                (Dimension.RELIABILITY, "reliability_score", rel),
            ]:
                transactions.append(
                    TransactionRecord(
                        supplier_id=supplier.id,
                        data_source_id=data_source.id,
                        dimension=dim,
                        metric_name=metric_n,
                        metric_value=val,
                        record_date=rec_date,
                    )
                )

            # Generate alerts for at-risk vendors
            if overall < 75 or "crit" in risk_str or "risk" in risk_str or "high" in risk_str:
                dim_list = [("Delivery", deliv), ("Quality", qual), ("Pricing", cost), ("Reliability", rel)]
                min_dim, min_val = min(dim_list, key=lambda x: x[1])
                is_crit = overall < 65 or "crit" in risk_str
                direct_alerts_to_create.append(
                    AlertModel(
                        supplier_id=supplier.id,
                        rule_type=AlertRuleType.COMPOSITE,
                        severity=AlertSeverity.CRITICAL if is_crit else AlertSeverity.HIGH,
                        title=f"Critical Risk: Overall score {overall:.1f} ({tier})" if is_crit else f"At-Risk Alert: Score {overall:.1f} ({tier})",
                        description=(
                            f"Supplier {supplier.name} is categorized as {tier} with an overall score of {overall:.1f}. "
                            f"Performance is lagging significantly in {min_dim} ({min_val:.1f})."
                        ),
                        metric_value=overall,
                        threshold_value=70.0 if is_crit else 75.0,
                        suggested_action=f"Initiate operational risk review with {supplier.name} and review backup supply lines.",
                    )
                )

        # ─── Check Delivery dimension ───
        ship_dt_col = normalized_cols.get("shipdate") or normalized_cols.get("ship_date") or normalized_cols.get("actual_date")
        due_dt_col = normalized_cols.get("duedate") or normalized_cols.get("due_date") or normalized_cols.get("promised_date")

        if ship_dt_col and due_dt_col:
            s_date = _parse_date(row.get(ship_dt_col)) + date_offset
            d_date = _parse_date(row.get(due_dt_col)) + date_offset
            days_late = max(0, (s_date - d_date).days)
            on_time = 1.0 if (s_date - d_date).days <= 2 else 0.0

            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.DELIVERY,
                    metric_name="on_time_delivery",
                    metric_value=on_time,
                    record_date=rec_date,
                    raw_row_json=row.dropna().to_dict(),
                )
            )
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.DELIVERY,
                    metric_name="delivery_delay",
                    metric_value=float(days_late),
                    record_date=rec_date,
                )
            )
        elif "days_late" in normalized_cols or "delay" in normalized_cols:
            col = normalized_cols.get("days_late") or normalized_cols.get("delay")
            days_late = _clean_num(row.get(col), 0.0)
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.DELIVERY,
                    metric_name="delivery_delay",
                    metric_value=days_late,
                    record_date=rec_date,
                )
            )
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.DELIVERY,
                    metric_name="on_time_delivery",
                    metric_value=1.0 if days_late <= 2 else 0.0,
                    record_date=rec_date,
                )
            )

        # ─── Check Quality dimension ───
        reject_col = normalized_cols.get("reject_qty") or normalized_cols.get("rejects") or normalized_cols.get("defect_count")
        received_col = normalized_cols.get("received_qty") or normalized_cols.get("qty_received") or normalized_cols.get("qty") or normalized_cols.get("qty_ordered")

        if reject_col and received_col:
            rej = _clean_num(row.get(reject_col), 0.0)
            recv = _clean_num(row.get(received_col), 1.0)
            if recv > 0:
                defect_rate = rej / recv
                transactions.append(
                    TransactionRecord(
                        supplier_id=supplier.id,
                        data_source_id=data_source.id,
                        dimension=Dimension.QUALITY,
                        metric_name="defect_rate",
                        metric_value=defect_rate,
                        record_date=rec_date,
                    )
                )
        elif "defect_rate" in normalized_cols:
            dr = _clean_num(row.get(normalized_cols["defect_rate"]), 0.0)
            if dr > 1.0:  # e.g. 5% entered as 5
                dr = dr / 100.0
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.QUALITY,
                    metric_name="defect_rate",
                    metric_value=dr,
                    record_date=rec_date,
                )
            )

        # ─── Check Pricing dimension ───
        contract_p_col = normalized_cols.get("contractprice") or normalized_cols.get("contract_price") or normalized_cols.get("target_price")
        actual_p_col = normalized_cols.get("actualprice") or normalized_cols.get("actual_price") or normalized_cols.get("invoice_price") or normalized_cols.get("unit_price")

        if contract_p_col and actual_p_col:
            cp = _clean_num(row.get(contract_p_col))
            ap = _clean_num(row.get(actual_p_col))
            variance = (((ap - cp) / cp) * 100.0) if cp > 0 else 0.0
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.PRICING,
                    metric_name="unit_price",
                    metric_value=ap,
                    record_date=rec_date,
                )
            )
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.PRICING,
                    metric_name="price_variance",
                    metric_value=variance,
                    record_date=rec_date,
                )
            )
        elif actual_p_col:
            ap = _clean_num(row.get(actual_p_col))
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.PRICING,
                    metric_name="unit_price",
                    metric_value=ap,
                    record_date=rec_date,
                )
            )
        elif "price_variance" in normalized_cols or "price_var" in normalized_cols:
            col = normalized_cols.get("price_variance") or normalized_cols.get("price_var")
            pv = _clean_num(row.get(col), 0.0)
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.PRICING,
                    metric_name="price_variance",
                    metric_value=pv,
                    record_date=rec_date,
                )
            )

        # ─── Check Communication dimension ───
        resp_col = normalized_cols.get("response_time") or normalized_cols.get("response_hours") or normalized_cols.get("reply_time")
        if resp_col:
            rt = _clean_num(row.get(resp_col))
            transactions.append(
                TransactionRecord(
                    supplier_id=supplier.id,
                    data_source_id=data_source.id,
                    dimension=Dimension.COMMUNICATION,
                    metric_name="response_time_hours",
                    metric_value=rt,
                    record_date=rec_date,
                )
            )

    # Insert transactions
    for tx in transactions:
        db.add(tx)
    await db.flush()

    # 4. Compute scorecards and evaluate alerts for all affected suppliers
    store = ConfigStore(db, user_id=user_id)
    scoring_config = DEFAULT_SCORING_CONFIG
    alert_config = DEFAULT_ALERT_CONFIG

    scoring_engine = ScoringEngine(db)
    alert_engine = AlertEngine(db)

    total_alerts_fired = 0

    for sup_id in affected_suppliers:
        if sup_id in direct_scores_by_supplier:
            try:
                await scoring_engine.save_snapshot(sup_id, direct_scores_by_supplier[sup_id])
            except Exception as e:
                logger.warning(f"Error saving direct score snapshot for supplier {sup_id}: {e}")
        else:
            # Score supplier
            try:
                score = await scoring_engine.score_supplier(sup_id, scoring_config)
                await scoring_engine.save_snapshot(sup_id, score)

                # Evaluate alerts
                fired_alerts = await alert_engine.evaluate_all_rules(
                    sup_id,
                    alert_config,
                    composite_score=score,
                )

                for fa in fired_alerts:
                    # Map string to enum
                    rule_enum = AlertRuleType.DELAY
                    for r in AlertRuleType:
                        if r.value == fa.rule_type:
                            rule_enum = r
                            break

                    sev_enum = AlertSeverity.MEDIUM
                    for s in AlertSeverity:
                        if s.value == fa.severity:
                            sev_enum = s
                            break

                    alert_record = AlertModel(
                        supplier_id=fa.supplier_id,
                        rule_type=rule_enum,
                        severity=sev_enum,
                        title=fa.title,
                        description=fa.description,
                        metric_value=fa.metric_value,
                        threshold_value=fa.threshold_value,
                        suggested_action=fa.suggested_action,
                        data_points_json={"data_points": fa.data_points} if fa.data_points else None,
                    )
                    db.add(alert_record)
                    await db.flush()  # Ensure alert_record.id is generated
                    total_alerts_fired += 1

                    # Dispatch email for HIGH/CRITICAL alerts
                    if sev_enum in (AlertSeverity.HIGH, AlertSeverity.CRITICAL) and is_email_configured():
                        supplier = affected_suppliers[sup_id]
                        try:
                            await send_alert_email(AlertEmailData(
                                alert_id=alert_record.id,
                                supplier_name=supplier.name,
                                rule_type=fa.rule_type,
                                severity=fa.severity,
                                title=fa.title,
                                description=fa.description or "",
                                metric_value=fa.metric_value,
                                threshold_value=fa.threshold_value,
                                suggested_action=fa.suggested_action or "",
                            ))
                            alert_record.email_sent = True
                        except Exception as email_err:
                            logger.warning(f"Failed to send alert email for {fa.title}: {email_err}")
            except Exception as e:
                logger.warning(f"Error computing scores/alerts for supplier {sup_id}: {e}")

    # Save direct alerts generated for pre-scored at-risk suppliers
    for alert_rec in direct_alerts_to_create:
        db.add(alert_rec)
        total_alerts_fired += 1
    await db.flush()

    await db.commit()

    return {
        "status": "success",
        "row_count": len(df),
        "transactions_created": len(transactions),
        "suppliers_count": len(affected_suppliers),
        "alerts_fired": total_alerts_fired,
        "message": f"Successfully ingested {len(df)} rows across {len(affected_suppliers)} suppliers. Recomputed scorecards and evaluated alerts.",
    }


async def seed_sample_datasets(db: AsyncSession, user_id: str = "dev-user") -> dict:
    """
    Seed a comprehensive synthetic supplier dataset covering all 5 dimensions.
    Uses dynamic dates anchored to current time so alerts and scorecards reflect active data.
    Data is scoped to the given user_id for tenant isolation.
    """
    # Ensure default configurations are approved so the agent has active baselines
    store = ConfigStore(db, user_id=user_id)
    if not await store.get_active("scoring_weights"):
        sc_prop = await store.propose("scoring_weights", DEFAULT_SCORING_CONFIG.model_dump())
        await store.approve(sc_prop.id, approved_by="system_seed")
    if not await store.get_active("alert_rules"):
        al_prop = await store.propose("alert_rules", DEFAULT_ALERT_CONFIG.model_dump())
        await store.approve(al_prop.id, approved_by="system_seed")
    await db.commit()

    now = datetime.now(timezone.utc)
    t_60 = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    t_30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    t_5 = (now - timedelta(days=5)).strftime("%Y-%m-%d")

    # Dates with deliberate shipment delays
    t_60_late = (now - timedelta(days=55)).strftime("%Y-%m-%d")
    t_30_late = (now - timedelta(days=22)).strftime("%Y-%m-%d")
    t_5_late = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    sample_records = [
        # Acme Packaging (Good delivery, but defect spike recently)
        {"SupplierName": "Acme Packaging", "Category": "Packaging", "Region": "North America", "DueDate": t_60, "ShipDate": t_60, "Qty_Ordered": 500, "Qty_Received": 500, "Reject_Qty": 4, "ContractPrice": 12.0, "ActualPrice": 12.0, "Response_Hours": 8.0},
        {"SupplierName": "Acme Packaging", "Category": "Packaging", "Region": "North America", "DueDate": t_30, "ShipDate": t_30, "Qty_Ordered": 300, "Qty_Received": 300, "Reject_Qty": 5, "ContractPrice": 12.0, "ActualPrice": 12.5, "Response_Hours": 12.0},
        {"SupplierName": "Acme Packaging", "Category": "Packaging", "Region": "North America", "DueDate": t_5, "ShipDate": t_5, "Qty_Ordered": 200, "Qty_Received": 190, "Reject_Qty": 22, "ContractPrice": 12.0, "ActualPrice": 13.5, "Response_Hours": 32.0},

        # Beta Micro Corp (High volume electronics, steady high quality, on-time delivery)
        {"SupplierName": "Beta Micro Corp", "Category": "Electronics", "Region": "Asia Pacific", "DueDate": t_60, "ShipDate": t_60, "Qty_Ordered": 1000, "Qty_Received": 1000, "Reject_Qty": 2, "ContractPrice": 45.0, "ActualPrice": 45.0, "Response_Hours": 4.0},
        {"SupplierName": "Beta Micro Corp", "Category": "Electronics", "Region": "Asia Pacific", "DueDate": t_30, "ShipDate": t_30, "Qty_Ordered": 800, "Qty_Received": 800, "Reject_Qty": 3, "ContractPrice": 45.0, "ActualPrice": 44.8, "Response_Hours": 5.5},
        {"SupplierName": "Beta Micro Corp", "Category": "Electronics", "Region": "Asia Pacific", "DueDate": t_5, "ShipDate": t_5, "Qty_Ordered": 600, "Qty_Received": 600, "Reject_Qty": 1, "ContractPrice": 45.0, "ActualPrice": 45.0, "Response_Hours": 6.0},

        # Gamma Precision Works (Chronic delivery delays, late shipments)
        {"SupplierName": "Gamma Precision Works", "Category": "Machining", "Region": "Europe", "DueDate": t_60, "ShipDate": t_60_late, "Qty_Ordered": 400, "Qty_Received": 380, "Reject_Qty": 8, "ContractPrice": 85.0, "ActualPrice": 85.0, "Response_Hours": 18.0},
        {"SupplierName": "Gamma Precision Works", "Category": "Machining", "Region": "Europe", "DueDate": t_30, "ShipDate": t_30_late, "Qty_Ordered": 250, "Qty_Received": 240, "Reject_Qty": 12, "ContractPrice": 85.0, "ActualPrice": 92.0, "Response_Hours": 28.0},
        {"SupplierName": "Gamma Precision Works", "Category": "Machining", "Region": "Europe", "DueDate": t_5, "ShipDate": t_5_late, "Qty_Ordered": 150, "Qty_Received": 145, "Reject_Qty": 15, "ContractPrice": 85.0, "ActualPrice": 96.0, "Response_Hours": 44.0},

        # Nova Polymers (Quality defects & price hike)
        {"SupplierName": "Nova Polymers Corp", "Category": "Raw Materials", "Region": "North America", "DueDate": t_60, "ShipDate": t_60, "Qty_Ordered": 1200, "Qty_Received": 1200, "Reject_Qty": 14, "ContractPrice": 8.5, "ActualPrice": 8.5, "Response_Hours": 10.0},
        {"SupplierName": "Nova Polymers Corp", "Category": "Raw Materials", "Region": "North America", "DueDate": t_30, "ShipDate": t_30, "Qty_Ordered": 900, "Qty_Received": 900, "Reject_Qty": 45, "ContractPrice": 8.5, "ActualPrice": 8.9, "Response_Hours": 22.0},
        {"SupplierName": "Nova Polymers Corp", "Category": "Raw Materials", "Region": "North America", "DueDate": t_5, "ShipDate": t_5, "Qty_Ordered": 750, "Qty_Received": 750, "Reject_Qty": 68, "ContractPrice": 8.5, "ActualPrice": 9.8, "Response_Hours": 36.0},

        # Apex Freight Logistics (Fast delivery, competitive pricing)
        {"SupplierName": "Apex Freight Logistics", "Category": "Logistics", "Region": "Global", "DueDate": t_60, "ShipDate": t_60, "Qty_Ordered": 100, "Qty_Received": 100, "Reject_Qty": 0, "ContractPrice": 150.0, "ActualPrice": 148.0, "Response_Hours": 2.5},
        {"SupplierName": "Apex Freight Logistics", "Category": "Logistics", "Region": "Global", "DueDate": t_30, "ShipDate": t_30, "Qty_Ordered": 120, "Qty_Received": 120, "Reject_Qty": 0, "ContractPrice": 150.0, "ActualPrice": 150.0, "Response_Hours": 3.0},
        {"SupplierName": "Apex Freight Logistics", "Category": "Logistics", "Region": "Global", "DueDate": t_5, "ShipDate": t_5, "Qty_Ordered": 150, "Qty_Received": 150, "Reject_Qty": 0, "ContractPrice": 150.0, "ActualPrice": 149.0, "Response_Hours": 2.0},
    ]

    df = pd.DataFrame(sample_records)
    return await ingest_dataframe(df, db, source_name="Sample Benchmark Dataset", user_id=user_id)

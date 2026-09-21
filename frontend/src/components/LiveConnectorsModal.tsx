"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Cable,
  Database,
  FileSpreadsheet,
  Upload,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface LiveConnectorsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenUpload?: () => void;
}

export default function LiveConnectorsModal({
  open,
  onOpenChange,
  onOpenUpload,
}: LiveConnectorsModalProps) {
  const [notified, setNotified] = useState(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-zinc-950 border border-zinc-800 text-zinc-100 p-6 rounded-md shadow-2xl">
        <DialogHeader className="pb-3 border-b border-zinc-900">
          <div className="flex items-center justify-between">
            <span className="technical-label flex items-center gap-1.5 text-orange-400">
              <Cable className="w-3.5 h-3.5" />
              LIVE CONNECTORS
            </span>
            <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-orange-500/10 border border-orange-500/30 text-orange-400 font-semibold uppercase">
              COMING SOON
            </span>
          </div>
          <DialogTitle className="text-base font-bold text-zinc-100 mt-1">
            ERP &amp; Cloud Sheets Sync
          </DialogTitle>
        </DialogHeader>

        {/* Short Generic Sarcastic Text */}
        <div className="my-4 bg-zinc-900/60 border border-zinc-800 rounded p-4 text-center space-y-2">
          <p className="text-xs text-zinc-300 font-medium leading-relaxed">
            Direct integration with SAP, NetSuite, Coupa &amp; Google Sheets is on the roadmap.
          </p>
          <p className="text-xs text-zinc-500 italic">
            Because why drag-and-drop a CSV in 2 seconds when you could spend 6 months waiting for IT to approve an API token?
          </p>
        </div>

        {/* Minimal Connectors List */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono-data">
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded px-3 py-2 flex items-center gap-2 text-zinc-300">
            <Database className="w-3.5 h-3.5 text-orange-400 shrink-0" />
            <span className="truncate">SAP &amp; NetSuite</span>
          </div>
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded px-3 py-2 flex items-center gap-2 text-zinc-300">
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="truncate">Google Sheets</span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-4 mt-4 border-t border-zinc-900 flex items-center justify-end gap-2">
          {onOpenUpload && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                onOpenChange(false);
                onOpenUpload();
              }}
              className="h-8 px-3 text-xs bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
            >
              <Upload className="w-3.5 h-3.5 mr-1.5" />
              Just Upload CSV
            </Button>
          )}

          <Button
            size="sm"
            onClick={() => setNotified(true)}
            disabled={notified}
            className={`h-8 px-3 text-xs font-mono-data ${
              notified
                ? "bg-emerald-600 text-white"
                : "bg-orange-600 hover:bg-orange-500 text-white"
            }`}
          >
            {notified ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                Noted
              </>
            ) : (
              <>
                <span>Notify Me</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

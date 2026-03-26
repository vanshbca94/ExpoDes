import { useState } from "react";
import { Shell } from "@/components/layout/Shell";
import { useSendBroadcast } from "@workspace/api-client-react";
import { Radio, Send, Info, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function Broadcast() {
  const [message, setMessage] = useState("");
  const { mutate, isPending, data: result, reset } = useSendBroadcast();

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    mutate({ data: { message, parse_mode: 'HTML' } });
  };

  return (
    <Shell title="Network Broadcast" subtitle="Send announcements to all active chats">
      <div className="max-w-3xl mx-auto">
        <div className="glass p-8 rounded-3xl border border-white/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-12 bg-primary/10 blur-[100px] rounded-full w-64 h-64 pointer-events-none" />
          
          <div className="flex items-center gap-4 mb-8">
            <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center text-primary border border-primary/30 shadow-lg shadow-primary/20">
              <Radio className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-display font-bold">Compose Message</h2>
              <p className="text-muted-foreground">Supports HTML formatting</p>
            </div>
          </div>

          <form onSubmit={handleSend} className="space-y-6 relative z-10">
            <div>
              <textarea
                value={message}
                onChange={(e) => { setMessage(e.target.value); reset(); }}
                placeholder="<b>Hello everyone!</b>&#10;&#10;New update is live..."
                rows={8}
                className="w-full p-4 bg-background/50 backdrop-blur-sm border border-border rounded-2xl focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all font-mono text-sm resize-none"
              />
              <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                <Info className="w-4 h-4" /> Use &lt;b&gt;, &lt;i&gt;, &lt;a href="..."&gt; for formatting.
              </div>
            </div>

            <button
              type="submit"
              disabled={isPending || !message.trim()}
              className="w-full py-4 bg-gradient-to-r from-primary to-blue-400 text-white font-bold rounded-2xl shadow-xl shadow-primary/25 hover:shadow-primary/40 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center gap-2 text-lg"
            >
              {isPending ? (
                <span className="animate-pulse">Broadcasting to network...</span>
              ) : (
                <>
                  <Send className="w-5 h-5" /> Send to All Chats
                </>
              )}
            </button>
          </form>

          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, height: 0, marginTop: 0 }}
                animate={{ opacity: 1, height: 'auto', marginTop: 24 }}
                exit={{ opacity: 0, height: 0, marginTop: 0 }}
                className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl"
              >
                <div className="flex items-center gap-3 text-emerald-400 font-bold mb-2">
                  <CheckCircle className="w-5 h-5" /> Broadcast Complete
                </div>
                <div className="flex justify-between text-sm text-foreground">
                  <span>Successfully delivered: <span className="text-emerald-400 font-bold">{result.sent}</span></span>
                  <span>Failed/Blocked: <span className="text-red-400 font-bold">{result.failed}</span></span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </Shell>
  );
}

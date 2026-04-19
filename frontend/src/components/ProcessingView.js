import { useEffect, useState } from "react";
import { getStatus, wsProgress } from "../api";

export default function ProcessingView({ jobId, onComplete }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("processing");

  useEffect(() => {
    let cancelled = false;
    const ws = new WebSocket(wsProgress(jobId));
    const syncStatus = async () => {
      try {
        const { data } = await getStatus(jobId);
        if (cancelled) return;
        setProgress(data.progress);
        setStatus(data.status);
        if (data.status === "completed") {
          ws.close();
          onComplete();
        }
      } catch {
        if (!cancelled) {
          setStatus("failed");
        }
      }
    };

    const pollId = setInterval(syncStatus, 2000);

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setProgress(msg.progress);
      setStatus(msg.status);
      if (msg.status === "completed") {
        ws.close();
        onComplete();
      } else if (msg.status === "failed") {
        ws.close();
      }
    };

    ws.onerror = () => ws.close();
    syncStatus();

    return () => {
      cancelled = true;
      clearInterval(pollId);
      ws.close();
    };
  }, [jobId, onComplete]);

  return (
    <div className="page processing-page">
      <h2>Processing Video…</h2>
      <div className="progress-bar-wrap">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
      </div>
      <p className="progress-label">Processing… {progress}%</p>
      {status === "failed" && <p className="error">Processing failed. Please try again.</p>}
    </div>
  );
}

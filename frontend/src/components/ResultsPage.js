import { useEffect, useState } from "react";
import { getResult, downloadReport, getVideoUrl } from "../api";

export default function ResultsPage({ jobId, onReset }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getResult(jobId)
      .then(({ data }) => setResult(data))
      .catch(() => setError("Failed to load results"));
  }, [jobId]);

  if (error) return <div className="page"><p className="error">{error}</p></div>;
  if (!result) return <div className="page"><p>Loading results…</p></div>;

  const { total_count, counts_by_type, processing_time } = result;

  return (
    <div className="page results-page">
      <h2>Analysis Results</h2>

      <div className="stats-grid">
        <div className="stat-card total">
          <span className="stat-value">{total_count}</span>
          <span className="stat-label">Total Vehicles</span>
        </div>
        {Object.entries(counts_by_type).map(([type, count]) => (
          <div key={type} className="stat-card">
            <span className="stat-value">{count}</span>
            <span className="stat-label">{type}</span>
          </div>
        ))}
        <div className="stat-card">
          <span className="stat-value">{processing_time}s</span>
          <span className="stat-label">Processing Time</span>
        </div>
      </div>

      <div className="video-wrap">
        <video controls autoPlay src={getVideoUrl(jobId)} width="100%" type="video/mp4" />
      </div>

      <div className="actions">
        <a href={downloadReport(jobId)} download className="btn-download">
          ⬇ Download CSV Report
        </a>
        <button onClick={onReset} className="btn-reset">Analyze Another Video</button>
      </div>
    </div>
  );
}

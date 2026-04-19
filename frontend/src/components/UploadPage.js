import { useState } from "react";
import { uploadVideo, startProcessing } from "../api";

export default function UploadPage({ onJobStart }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const { data: uploaded } = await uploadVideo(file);
      await startProcessing(uploaded.job_id);
      onJobStart(uploaded.job_id);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        (err.message === "Network Error"
          ? "Cannot reach the backend. Make sure the API server is running on port 8000."
          : "Upload failed")
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page upload-page">
      <h1>Drone Traffic Analyzer</h1>
      <form onSubmit={handleSubmit} className="upload-form">
        <label className="file-label">
          {file ? file.name : "Choose .mp4 video"}
          <input
            type="file"
            accept=".mp4"
            onChange={(e) => setFile(e.target.files[0])}
            hidden
          />
        </label>
        <button type="submit" disabled={!file || loading}>
          {loading ? "Uploading…" : "Upload & Analyze"}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}

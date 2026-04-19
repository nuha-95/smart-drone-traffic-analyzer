import axios from "axios";

const fallbackBase =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";

const BASE = (process.env.REACT_APP_API_BASE_URL || fallbackBase).replace(/\/$/, "");
const WS_BASE = BASE.replace(/^http/i, (protocol) =>
  protocol.toLowerCase() === "https" ? "wss" : "ws"
);

export const uploadVideo = (file) => {
  const form = new FormData();
  form.append("file", file);
  return axios.post(`${BASE}/upload`, form);
};

export const startProcessing = (jobId) =>
  axios.post(`${BASE}/process/${jobId}`);

export const getStatus = (jobId) =>
  axios.get(`${BASE}/status/${jobId}`);

export const getResult = (jobId) =>
  axios.get(`${BASE}/result/${jobId}`);

export const downloadReport = (jobId) =>
  `${BASE}/download/${jobId}`;

export const getVideoUrl = (jobId) =>
  `${BASE}/video/${jobId}`;

export const wsProgress = (jobId) =>
  `${WS_BASE}/ws/${jobId}`;

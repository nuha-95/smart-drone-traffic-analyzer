import { useEffect, useState } from "react";
import UploadPage from "./components/UploadPage";
import ProcessingView from "./components/ProcessingView";
import ResultsPage from "./components/ResultsPage";
import "./App.css";

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="theme-icon">
      <circle cx="12" cy="12" r="4.5" fill="currentColor" />
      <path
        d="M12 1.75v2.5M12 19.75v2.5M4.75 12h-2.5M21.75 12h-2.5M19.25 4.75l-1.77 1.77M6.52 17.48l-1.77 1.77M19.25 19.25l-1.77-1.77M6.52 6.52L4.75 4.75"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="theme-icon">
      <path
        d="M14.5 2.75a8.75 8.75 0 1 0 6.75 14.32A9.5 9.5 0 1 1 14.5 2.75Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [view, setView] = useState("upload"); // upload | processing | results
  const [jobId, setJobId] = useState(null);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
    }
  }, []);

  useEffect(() => {
    document.body.dataset.theme = theme;
    window.localStorage.setItem("theme", theme);
  }, [theme]);

  const handleJobStart = (id) => {
    setJobId(id);
    setView("processing");
  };

  const handleComplete = () => setView("results");
  const handleReset = () => { setJobId(null); setView("upload"); };
  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  return (
    <div className="app">
      <button
        type="button"
        className="theme-toggle"
        onClick={toggleTheme}
        aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        aria-pressed={theme === "light"}
      >
        <span className={`theme-toggle-track ${theme === "light" ? "is-light" : ""}`}>
          <span className="theme-toggle-thumb">
            {theme === "dark" ? <MoonIcon /> : <SunIcon />}
          </span>
        </span>
      </button>
      {view === "upload" && <UploadPage onJobStart={handleJobStart} />}
      {view === "processing" && <ProcessingView jobId={jobId} onComplete={handleComplete} />}
      {view === "results" && <ResultsPage jobId={jobId} onReset={handleReset} />}
    </div>
  );
}

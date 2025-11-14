import React, { useState } from "react";

const API_BASE_URL = "https://smart-ats-c-v.onrender.com";

const Home: React.FC = () => {
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [manualText, setManualText] = useState("");
  const [method, setMethod] = useState<"upload" | "manual">("upload");
  const [outputLanguage, setOutputLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);

    const formData = new FormData();

    if (method === "upload") {
      if (!cvFile) {
        setError("Please select a file.");
        setLoading(false);
        return;
      }
      formData.append("cv_file", cvFile);
    } else {
      if (!manualText.trim()) {
        setError("Please enter CV text.");
        setLoading(false);
        return;
      }
      const textBlob = new Blob([manualText], { type: "text/plain" });
      formData.append("cv_file", textBlob, "manual_input.txt");
    }

    formData.append("output_language", outputLanguage);
    formData.append("template_style", "professional-blue");
    formData.append("target_job_description", "");
    formData.append("postleitzahl", "");

    try {
      const response = await fetch(`${API_BASE_URL}/analyze-and-rewrite/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text);
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto", padding: "20px" }}>
      <h1 style={{ fontSize: "32px", marginBottom: "20px" }}>
        Smart CV Analyzer
      </h1>

      {/* Method Switch */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
        <button
          onClick={() => setMethod("upload")}
          style={{
            padding: "10px 20px",
            background: method === "upload" ? "#1e40af" : "#ccc",
            color: "white",
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
          }}
        >
          Upload File
        </button>

        <button
          onClick={() => setMethod("manual")}
          style={{
            padding: "10px 20px",
            background: method === "manual" ? "#1e40af" : "#ccc",
            color: "white",
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
          }}
        >
          Manual Input
        </button>
      </div>

      {/* Upload Section */}
      {method === "upload" && (
        <input
          type="file"
          accept=".pdf,.doc,.docx"
          onChange={(e) => {
            if (e.target.files) setCvFile(e.target.files[0]);
          }}
        />
      )}

      {/* Manual Section */}
      {method === "manual" && (
        <textarea
          value={manualText}
          onChange={(e) => setManualText(e.target.value)}
          placeholder="Paste your CV text here..."
          style={{
            width: "100%",
            height: "200px",
            padding: "10px",
            borderRadius: "6px",
            border: "1px solid #999",
          }}
        />
      )}

      {/* Language */}
      <div style={{ margin: "20px 0" }}>
        <label>Output Language: </label>
        <select
          value={outputLanguage}
          onChange={(e) => setOutputLanguage(e.target.value)}
          style={{ marginLeft: "10px", padding: "6px" }}
        >
          <option value="en">English</option>
          <option value="de">German</option>
          <option value="ar">Arabic</option>
        </select>
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={loading}
        style={{
          width: "100%",
          padding: "15px",
          background: "#1e40af",
          color: "white",
          borderRadius: "8px",
          border: "none",
          fontSize: "18px",
          cursor: "pointer",
        }}
      >
        {loading ? "Analyzing..." : "Analyze CV"}
      </button>

      {/* Error */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Result */}
      {result && (
        <div style={{ marginTop: "30px" }}>
          <h2>Result:</h2>
          <pre
            style={{
              background: "#f0f0f0",
              padding: "20px",
              borderRadius: "10px",
            }}
          >
{JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default Home;

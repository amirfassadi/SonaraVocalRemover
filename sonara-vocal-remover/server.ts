import express from "express";
import path from "path";
import multer from "multer";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 200 * 1024 * 1024 } // 200MB limit
});

const getSeparationApiUrl = () => {
  let url = process.env.SEPARATION_API_URL || "http://localhost:8000";
  return url.endsWith("/") ? url.slice(0, -1) : url;
};

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// 1. Health check endpoint
app.get("/api/health", async (req, res) => {
  const backendUrl = getSeparationApiUrl();
  try {
    const response = await fetch(`${backendUrl}/api/health`, {
      method: "GET",
      headers: { "Accept": "application/json" }
    });

    if (response.ok) {
      const data = await response.json();
      return res.json({
        status: data.status || "ok",
        version: data.version || "1.0.0",
        engine: data.engine || "htdemucs",
        supported_formats: data.supported_formats || ["wav", "mp3", "flac", "m4a", "ogg"],
        backend_url: backendUrl,
        connected: true
      });
    } else {
      return res.status(response.status).json({
        status: "error",
        connected: false,
        backend_url: backendUrl,
        error: {
          type: "BackendStatusError",
          message: `Separation backend returned HTTP ${response.status}`
        }
      });
    }
  } catch (err: any) {
    return res.status(503).json({
      status: "unreachable",
      connected: false,
      backend_url: backendUrl,
      error: {
        type: "NetworkError",
        message: "Can't reach the separation service right now. Please try again shortly."
      }
    });
  }
});

// 2. Validate URL endpoint
app.post("/api/validate-url", async (req, res) => {
  const backendUrl = getSeparationApiUrl();
  const { url } = req.body;

  if (!url || typeof url !== "string") {
    return res.status(400).json({
      valid: false,
      error: {
        type: "InvalidUrlError",
        message: "That doesn't look like a valid URL."
      }
    });
  }

  try {
    const response = await fetch(`${backendUrl}/api/validate-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (err: any) {
    // If backend is unreachable, do local client-friendly validation
    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        return res.status(400).json({
          valid: false,
          error: {
            type: "UnsupportedUrlSchemeError",
            message: "Only http:// and https:// URLs are supported."
          }
        });
      }
      const host = parsed.hostname.toLowerCase();
      if (
        host.includes("youtube.com") ||
        host.includes("youtu.be") ||
        host.includes("spotify.com") ||
        host.includes("soundcloud.com")
      ) {
        return res.status(400).json({
          valid: false,
          isPlatformUrl: true,
          error: {
            type: "BlockedUrlError",
            message: "That URL can't be used (platform pages like YouTube/Spotify are not supported — direct audio files only)."
          }
        });
      }
    } catch (e) {}

    return res.status(503).json({
      valid: false,
      error: {
        type: "NetworkError",
        message: "Can't reach the separation service right now. Please try again shortly."
      }
    });
  }
});

// 3. Separate Audio Endpoint (Proxying file upload or URL)
app.post("/api/separate", upload.single("file"), async (req, res) => {
  const backendUrl = getSeparationApiUrl();

  try {
    const formData = new FormData();

    if (req.file) {
      const blob = new Blob([req.file.buffer], { type: req.file.mimetype || "audio/wav" });
      formData.append("file", blob, req.file.originalname);
    } else if (req.body.url) {
      formData.append("url", req.body.url);
    } else {
      return res.status(400).json({
        error: {
          type: "InvalidLocalFileError",
          message: "No audio file or URL was provided."
        }
      });
    }

    if (req.body.model) formData.append("model", req.body.model);
    if (req.body.device) formData.append("device", req.body.device);

    const response = await fetch(`${backendUrl}/api/separate`, {
      method: "POST",
      body: formData
    });

    const responseText = await response.text();
    let data: any = {};
    try {
      data = JSON.parse(responseText);
    } catch (e) {
      return res.status(response.status || 500).json({
        error: {
          type: "ProcessingFailureError",
          message: `Separation backend returned invalid response: ${responseText.slice(0, 100)}`
        }
      });
    }

    if (!response.ok) {
      return res.status(response.status).json(data);
    }

    // Rewrite relative URLs so browser routes through Express proxy
    let vocals_url = data.vocals_url || "";
    let instrumental_url = data.instrumental_url || "";

    if (vocals_url.startsWith("/")) {
      vocals_url = `/api${vocals_url.startsWith("/api") ? "" : ""}${vocals_url}`;
    }
    if (instrumental_url.startsWith("/")) {
      instrumental_url = `/api${instrumental_url.startsWith("/api") ? "" : ""}${instrumental_url}`;
    }

    return res.json({
      job_id: data.job_id,
      vocals_url,
      instrumental_url,
      model: data.model || req.body.model || "htdemucs",
      device: data.device || req.body.device || "cpu",
      source_origin: data.source_origin || (req.file ? "file" : "url")
    });

  } catch (err: any) {
    console.error("Separation Proxy Error:", err);
    return res.status(503).json({
      error: {
        type: "NetworkError",
        message: "Can't reach the separation service right now. Please try again shortly."
      }
    });
  }
});

// 4. File proxy for audio stem downloads and playback
app.get(["/api/files/:jobId/:filename", "/files/:jobId/:filename"], async (req, res) => {
  const backendUrl = getSeparationApiUrl();
  const { jobId, filename } = req.params;

  try {
    const targetUrl = `${backendUrl}/files/${jobId}/${filename}`;
    const response = await fetch(targetUrl);

    if (!response.ok) {
      return res.status(response.status).json({
        error: {
          type: "ProcessingFailureError",
          message: `Stem file not found or inaccessible on separation server.`
        }
      });
    }

    res.setHeader("Content-Type", response.headers.get("Content-Type") || "audio/wav");
    if (response.headers.has("Content-Length")) {
      res.setHeader("Content-Length", response.headers.get("Content-Length")!);
    }
    res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);

    if (response.body) {
      const reader = (response.body as any).getReader();
      const pump = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          res.write(value);
        }
        res.end();
      };
      await pump();
    } else {
      res.end();
    }
  } catch (err: any) {
    return res.status(503).json({
      error: {
        type: "NetworkError",
        message: "Can't reach the separation service right now. Please try again shortly."
      }
    });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Sonara Vocal Remover Web App running on http://0.0.0.0:${PORT}`);
    console.log(`Configured SEPARATION_API_URL: ${getSeparationApiUrl()}`);
  });
}

startServer();

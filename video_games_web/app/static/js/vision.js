(() => {
  const form = document.getElementById("vision-form");
  if (!form) {
    return;
  }

  const video = document.getElementById("vision-video");
  const preview = document.getElementById("vision-preview");
  const placeholder = document.getElementById("vision-placeholder");
  const fileInput = document.getElementById("vision-file");
  const sourceInput = document.getElementById("vision-source");
  const startButton = document.getElementById("vision-start");
  const captureButton = document.getElementById("vision-capture");
  const stopButton = document.getElementById("vision-stop");
  const submitButton = document.getElementById("vision-submit");
  const statusBox = document.getElementById("vision-status");
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const canvas = document.createElement("canvas");

  let stream = null;
  let capturedBlob = null;
  let capturedUrl = null;
  let sending = false;

  function showError(message) {
    statusBox.textContent = message;
    statusBox.classList.remove("d-none");
  }

  function clearError() {
    statusBox.textContent = "";
    statusBox.classList.add("d-none");
  }

  function updateSubmitState() {
    const hasFile = fileInput.files && fileInput.files.length > 0;
    submitButton.disabled = sending || (!hasFile && !capturedBlob);
  }

  function showPlaceholder() {
    placeholder.classList.remove("d-none");
    video.classList.add("d-none");
    preview.classList.add("d-none");
  }

  function showImage(url) {
    preview.src = url;
    preview.classList.remove("d-none");
    video.classList.add("d-none");
    placeholder.classList.add("d-none");
  }

  function releaseCaptured() {
    if (capturedUrl) {
      URL.revokeObjectURL(capturedUrl);
      capturedUrl = null;
    }
    capturedBlob = null;
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
    video.srcObject = null;
    startButton.disabled = false;
    captureButton.disabled = true;
    stopButton.disabled = true;
    if (capturedBlob) {
      showImage(capturedUrl);
    } else if (fileInput.files && fileInput.files.length > 0) {
      showImage(URL.createObjectURL(fileInput.files[0]));
    } else {
      showPlaceholder();
    }
  }

  async function startCamera() {
    clearError();
    if (!window.isSecureContext) {
      showError("La camara requiere HTTPS o ejecutar la app en localhost.");
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError("Este navegador no permite acceder a la camara.");
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      video.srcObject = stream;
      video.classList.remove("d-none");
      preview.classList.add("d-none");
      placeholder.classList.add("d-none");
      startButton.disabled = true;
      captureButton.disabled = false;
      stopButton.disabled = false;
    } catch (error) {
      const message = error && error.name === "NotAllowedError"
        ? "Permiso de camara denegado. Revisa los permisos del navegador."
        : "No se pudo iniciar la camara.";
      showError(message);
    }
  }

  function captureFrame() {
    if (!stream || !video.videoWidth) {
      showError("La camara todavia no esta lista. Intenta de nuevo.");
      return;
    }
    clearError();

    const maxSide = 960;
    const scale = Math.min(1, maxSide / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          showError("No se pudo capturar la imagen.");
          return;
        }
        releaseCaptured();
        capturedBlob = blob;
        capturedUrl = URL.createObjectURL(blob);
        fileInput.value = "";
        sourceInput.value = "camera";
        showImage(capturedUrl);
        updateSubmitState();
      },
      "image/jpeg",
      0.9
    );
  }

  fileInput.addEventListener("change", () => {
    clearError();
    releaseCaptured();
    sourceInput.value = "upload";
    if (fileInput.files && fileInput.files.length > 0) {
      stopCamera();
    } else {
      showPlaceholder();
    }
    updateSubmitState();
  });

  startButton.addEventListener("click", startCamera);
  captureButton.addEventListener("click", captureFrame);
  stopButton.addEventListener("click", stopCamera);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending) {
      return;
    }
    clearError();

    const file = fileInput.files && fileInput.files[0];
    let blob = file;
    let filename = file ? file.name : "captura.jpg";
    let source = "upload";

    if (!blob && capturedBlob) {
      blob = capturedBlob;
      filename = "captura.jpg";
      source = "camera";
    }

    if (!blob) {
      showError("Selecciona o captura una imagen antes de predecir.");
      return;
    }

    const formData = new FormData();
    formData.append("csrf_token", csrfMeta ? csrfMeta.content : "");
    formData.append("source", source);
    formData.append("image", blob, filename);

    sending = true;
    updateSubmitState();
    submitButton.textContent = "Clasificando...";

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      });

      let payload = null;
      try {
        payload = await response.json();
      } catch (error) {
        payload = null;
      }

      if (!response.ok) {
        throw new Error(
          (payload && payload.error) || `Error ${response.status} al clasificar la imagen.`
        );
      }
      if (!payload || !payload.redirect_url) {
        throw new Error("La respuesta del servidor no es valida.");
      }

      window.location.href = payload.redirect_url;
    } catch (error) {
      showError(error.message || "No se pudo clasificar la imagen.");
    } finally {
      sending = false;
      submitButton.textContent = "Clasificar imagen";
      updateSubmitState();
    }
  });

  window.addEventListener("beforeunload", () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
  });

  updateSubmitState();
})();

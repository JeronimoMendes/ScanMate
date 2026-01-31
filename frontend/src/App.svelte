<script>
  import { tick } from 'svelte';

  let videoElement;
  let canvasElement;
  let cameraContainer;
  let guideRect;
  let stream = null;
  let capturedImage = null;
  let capturedBlob = null;
  let fenResult = null;
  let error = null;
  let isLoading = false;
  let cameraStarted = false;

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });
      cameraStarted = true;
      await tick();
      videoElement.srcObject = stream;
      error = null;
    } catch (err) {
      error = 'Failed to access camera: ' + err.message;
    }
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
    cameraStarted = false;
  }

  function capturePhoto() {
    const vw = videoElement.videoWidth;
    const vh = videoElement.videoHeight;
    const container = cameraContainer.getBoundingClientRect();
    const guide = guideRect.getBoundingClientRect();

    const videoAspect = vw / vh;
    const containerAspect = container.width / container.height;

    let scale, cropOffsetX, cropOffsetY;

    if (videoAspect > containerAspect) {
      scale = container.height / vh;
      cropOffsetX = (vw * scale - container.width) / 2;
      cropOffsetY = 0;
    } else {
      scale = container.width / vw;
      cropOffsetX = 0;
      cropOffsetY = (vh * scale - container.height) / 2;
    }

    const guideX = guide.left - container.left;
    const guideY = guide.top - container.top;
    const guideSize = guide.width;

    const srcX = (guideX + cropOffsetX) / scale;
    const srcY = (guideY + cropOffsetY) / scale;
    const srcSize = guideSize / scale;

    canvasElement.width = srcSize;
    canvasElement.height = srcSize;
    const ctx = canvasElement.getContext('2d');
    ctx.drawImage(videoElement, srcX, srcY, srcSize, srcSize, 0, 0, srcSize, srcSize);

    capturedImage = canvasElement.toDataURL('image/jpeg', 0.9);
    canvasElement.toBlob(blob => {
      capturedBlob = blob;
    }, 'image/jpeg', 0.9);

    stopCamera();
  }

  function retakePhoto() {
    capturedImage = null;
    capturedBlob = null;
    fenResult = null;
    error = null;
    startCamera();
  }

  async function submitPhoto() {
    if (!capturedBlob) return;

    isLoading = true;
    error = null;

    try {
      const formData = new FormData();
      formData.append('board_file', capturedBlob, 'board.jpg');

      const response = await fetch('/api/fen', {
        method: 'POST',
        headers: {
          'Accept': 'application/json'
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      fenResult = data.fen || data;
    } catch (err) {
      error = 'Failed to analyze image: ' + err.message;
    } finally {
      isLoading = false;
    }
  }

  function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const img = new Image();
    img.onload = () => {
      const size = Math.min(img.width, img.height);
      const x = (img.width - size) / 2;
      const y = (img.height - size) / 2;

      canvasElement.width = size;
      canvasElement.height = size;
      const ctx = canvasElement.getContext('2d');
      ctx.drawImage(img, x, y, size, size, 0, 0, size, size);

      capturedImage = canvasElement.toDataURL('image/jpeg', 0.9);
      canvasElement.toBlob(blob => {
        capturedBlob = blob;
      }, 'image/jpeg', 0.9);
    };
    img.src = URL.createObjectURL(file);
  }

  function resetToStart() {
    capturedImage = null;
    capturedBlob = null;
    fenResult = null;
    error = null;
  }

  function openOnLichess() {
    const fenForUrl = fenResult.replace(/ /g, '_');
    window.open(`https://lichess.org/editor/${fenForUrl}`, '_blank');
  }
</script>

<main class="min-h-dvh bg-wood-dark text-cream p-5 flex flex-col font-sans safe-area">
  {#if error}
    <div class="bg-red-900/40 border border-red-800/50 text-red-200 px-4 py-3 rounded-2xl mb-4 text-sm">
      {error}
    </div>
  {/if}

  {#if !cameraStarted && !capturedImage}
    <div class="flex-1 flex flex-col items-center justify-center text-center max-w-sm mx-auto w-full">
      <div class="mb-6">
        <span class="text-5xl">♔</span>
      </div>
      <h1 class="text-3xl font-semibold text-cream mb-2 tracking-tight">
        ScanMate
      </h1>
      <p class="text-wood-muted text-sm mb-12">
        Snap a board, get the position
      </p>

      <div class="w-full space-y-3">
        <button
          on:click={startCamera}
          class="w-full py-4 px-6 bg-cream text-wood-dark font-semibold rounded-2xl transition-all active:scale-[0.98] active:bg-cream-dark shadow-lg shadow-black/20"
        >
          Start Camera
        </button>

        <div class="flex items-center gap-4 py-2">
          <div class="flex-1 h-px bg-wood-light/30"></div>
          <span class="text-wood-muted text-xs">or</span>
          <div class="flex-1 h-px bg-wood-light/30"></div>
        </div>

        <label class="block w-full py-4 px-6 bg-wood border border-wood-light/30 text-cream-muted font-medium rounded-2xl text-center cursor-pointer transition-all active:scale-[0.98] active:bg-wood-light/20">
          Choose from Gallery
          <input type="file" accept="image/*" on:change={handleFileSelect} class="hidden" />
        </label>
      </div>
    </div>
  {/if}

  {#if cameraStarted}
    <div class="flex-1 flex flex-col max-w-lg mx-auto w-full">
      <div bind:this={cameraContainer} class="relative max-h-[calc(100dvh-180px)] flex items-center justify-center bg-black rounded-2xl overflow-hidden border-2 border-wood-light/20">
        <video
          bind:this={videoElement}
          autoplay
          playsinline
          muted
          class="w-full h-full object-cover"
        ></video>
        <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div bind:this={guideRect} class="guide-rect w-[80%] max-w-[320px] aspect-square border-2 border-cream/70 rounded-lg"></div>
          <p class="absolute bottom-4 text-cream/60 text-xs">
            Align board within square
          </p>
        </div>
      </div>

      <div class="py-6 flex justify-center">
        <button
          on:click={capturePhoto}
          class="w-[72px] h-[72px] bg-cream rounded-full flex items-center justify-center transition-all active:scale-95 shadow-lg shadow-black/30"
        >
          <span class="w-14 h-14 bg-wood-dark rounded-full border-[3px] border-cream"></span>
        </button>
      </div>
    </div>
  {/if}

  {#if capturedImage && !fenResult}
    <div class="flex-1 flex flex-col max-w-sm mx-auto w-full">
      <div class="flex-1 flex items-center justify-center py-4">
        <img
          src={capturedImage}
          alt="Captured chess board"
          class="max-w-full max-h-[50vh] object-contain rounded-2xl border-2 border-wood-light/20"
        />
      </div>

      <div class="py-6 space-y-3">
        <p class="text-center text-wood-muted text-sm mb-4">Use this image?</p>
        <div class="flex gap-3">
          <button
            on:click={retakePhoto}
            class="flex-1 py-4 px-6 bg-wood border border-wood-light/30 text-cream-muted font-medium rounded-2xl transition-all active:scale-[0.98] active:bg-wood-light/20"
          >
            Retake
          </button>
          <button
            on:click={submitPhoto}
            disabled={isLoading}
            class="flex-1 py-4 px-6 bg-cream disabled:opacity-40 text-wood-dark font-semibold rounded-2xl transition-all active:scale-[0.98] active:bg-cream-dark shadow-lg shadow-black/20"
          >
            {isLoading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
      </div>
    </div>
  {/if}

  {#if fenResult}
    <div class="flex-1 flex flex-col max-w-sm mx-auto w-full">
      <div class="flex-1 flex flex-col justify-center py-4">
        <img
          src={capturedImage}
          alt="Analyzed chess board"
          class="max-w-full max-h-[35vh] object-contain rounded-2xl mx-auto mb-6 border-2 border-wood-light/20"
        />

        <div class="bg-wood border border-wood-light/30 p-4 rounded-2xl">
          <span class="block text-[11px] text-wood-muted uppercase tracking-wider mb-2">FEN Notation</span>
          <code class="block text-cream font-mono text-sm break-all leading-relaxed">
            {fenResult}
          </code>
        </div>
      </div>

      <div class="py-6 space-y-3">
        <button
          on:click={openOnLichess}
          class="w-full py-4 px-6 bg-cream text-wood-dark font-semibold rounded-2xl transition-all active:scale-[0.98] active:bg-cream-dark shadow-lg shadow-black/20"
        >
          Open on Lichess
        </button>
        <button
          on:click={resetToStart}
          class="w-full py-4 px-6 bg-wood border border-wood-light/30 text-cream-muted font-medium rounded-2xl transition-all active:scale-[0.98] active:bg-wood-light/20"
        >
          Scan Another
        </button>
      </div>
    </div>
  {/if}

  <canvas bind:this={canvasElement} class="hidden"></canvas>
</main>

<style>
  :global(html) {
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }

  :global(body) {
    background-color: #1a1512;
  }

  .safe-area {
    padding-top: max(1.25rem, env(safe-area-inset-top));
    padding-bottom: max(1.25rem, env(safe-area-inset-bottom));
  }

  .min-h-dvh {
    min-height: 100dvh;
  }

  .guide-rect {
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6);
  }

  /* Warm Wood Theme Colors */
  .bg-wood-dark {
    background-color: #1a1512;
  }

  .bg-wood {
    background-color: #2d2319;
  }

  .bg-wood-light\/20 {
    background-color: rgba(61, 47, 34, 0.2);
  }

  .border-wood-light\/20 {
    border-color: rgba(61, 47, 34, 0.2);
  }

  .border-wood-light\/30 {
    border-color: rgba(61, 47, 34, 0.3);
  }

  .bg-cream {
    background-color: #f5e6d3;
  }

  .bg-cream-dark {
    background-color: #e8d5c4;
  }

  .text-cream {
    color: #f5e6d3;
  }

  .text-cream-muted {
    color: #d4c4b0;
  }

  .text-cream\/60 {
    color: rgba(245, 230, 211, 0.6);
  }

  .text-cream\/70 {
    color: rgba(245, 230, 211, 0.7);
  }

  .border-cream {
    border-color: #f5e6d3;
  }

  .border-cream\/70 {
    border-color: rgba(245, 230, 211, 0.7);
  }

  .text-wood-dark {
    color: #1a1512;
  }

  .text-wood-muted {
    color: #8b7355;
  }

  .bg-wood-light\/30 {
    background-color: rgba(61, 47, 34, 0.3);
  }
</style>

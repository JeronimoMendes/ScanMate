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
    const ctx = canvasElement.getContext('2d');

    const videoWidth = videoElement.videoWidth;
    const videoHeight = videoElement.videoHeight;
    const containerRect = cameraContainer.getBoundingClientRect();
    const guideRectBounds = guideRect.getBoundingClientRect();

    const containerAspect = containerRect.width / containerRect.height;
    const videoAspect = videoWidth / videoHeight;

    let scale, offsetX, offsetY;

    if (videoAspect > containerAspect) {
      scale = containerRect.height / videoHeight;
      offsetX = (videoWidth * scale - containerRect.width) / 2;
      offsetY = 0;
    } else {
      scale = containerRect.width / videoWidth;
      offsetX = 0;
      offsetY = (videoHeight * scale - containerRect.height) / 2;
    }

    const guideX = guideRectBounds.left - containerRect.left;
    const guideY = guideRectBounds.top - containerRect.top;
    const guideSize = guideRectBounds.width;

    const srcX = (guideX + offsetX) / scale;
    const srcY = (guideY + offsetY) / scale;
    const srcSize = guideSize / scale;

    canvasElement.width = srcSize;
    canvasElement.height = srcSize;

    ctx.drawImage(
      videoElement,
      srcX, srcY, srcSize, srcSize,
      0, 0, srcSize, srcSize
    );

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

    capturedBlob = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      capturedImage = e.target.result;
    };
    reader.readAsDataURL(file);
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

<main class="min-h-dvh bg-neutral-950 text-neutral-200 p-5 flex flex-col font-sans safe-area">
  {#if error}
    <div class="bg-red-900/50 border border-red-800 text-red-200 px-4 py-3 rounded-lg mb-4 text-sm">
      {error}
    </div>
  {/if}

  {#if !cameraStarted && !capturedImage}
    <div class="flex-1 flex flex-col items-center justify-center text-center max-w-sm mx-auto w-full">
      <h1 class="text-2xl font-semibold text-neutral-100 mb-3">
        Chess Board Scanner
      </h1>
      <p class="text-neutral-500 text-sm mb-12">
        Capture a chess board to extract FEN notation
      </p>

      <div class="w-full space-y-3">
        <button
          on:click={startCamera}
          class="w-full py-4 px-6 bg-white text-neutral-900 font-medium rounded-xl transition-all active:scale-[0.98] active:bg-neutral-200"
        >
          Start Camera
        </button>

        <div class="flex items-center gap-4 py-2">
          <div class="flex-1 h-px bg-neutral-800"></div>
          <span class="text-neutral-600 text-xs">or</span>
          <div class="flex-1 h-px bg-neutral-800"></div>
        </div>

        <label class="block w-full py-4 px-6 bg-neutral-900 border border-neutral-800 text-neutral-300 font-medium rounded-xl text-center cursor-pointer transition-all active:scale-[0.98] active:bg-neutral-800">
          Choose from Gallery
          <input type="file" accept="image/*" on:change={handleFileSelect} class="hidden" />
        </label>
      </div>
    </div>
  {/if}

  {#if cameraStarted}
    <div class="flex-1 flex flex-col max-w-lg mx-auto w-full">
      <div
        bind:this={cameraContainer}
        class="relative flex-1 flex items-center justify-center bg-black rounded-xl overflow-hidden"
      >
        <video
          bind:this={videoElement}
          autoplay
          playsinline
          muted
          class="w-full h-full object-cover"
        ></video>
        <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div
            bind:this={guideRect}
            class="guide-rect w-[80%] max-w-[320px] aspect-square border-2 border-white/70 rounded"
          ></div>
          <p class="absolute bottom-4 text-white/60 text-xs">
            Align board within square
          </p>
        </div>
      </div>

      <div class="py-6 flex justify-center">
        <button
          on:click={capturePhoto}
          class="w-[72px] h-[72px] bg-white rounded-full flex items-center justify-center transition-all active:scale-95"
        >
          <span class="w-14 h-14 bg-neutral-950 rounded-full border-[3px] border-white"></span>
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
          class="max-w-full max-h-[50vh] object-contain rounded-xl"
        />
      </div>

      <div class="py-6 space-y-3">
        <p class="text-center text-neutral-400 text-sm mb-4">Use this image?</p>
        <div class="flex gap-3">
          <button
            on:click={retakePhoto}
            class="flex-1 py-4 px-6 bg-neutral-900 border border-neutral-800 text-neutral-300 font-medium rounded-xl transition-all active:scale-[0.98] active:bg-neutral-800"
          >
            Retake
          </button>
          <button
            on:click={submitPhoto}
            disabled={isLoading}
            class="flex-1 py-4 px-6 bg-white disabled:opacity-40 text-neutral-900 font-medium rounded-xl transition-all active:scale-[0.98] active:bg-neutral-200"
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
          class="max-w-full max-h-[35vh] object-contain rounded-xl mx-auto mb-6"
        />

        <div class="bg-neutral-900 border border-neutral-800 p-4 rounded-xl">
          <span class="block text-[11px] text-neutral-500 uppercase tracking-wider mb-2">FEN</span>
          <code class="block text-neutral-100 font-mono text-sm break-all leading-relaxed">
            {fenResult}
          </code>
        </div>
      </div>

      <div class="py-6 space-y-3">
        <button
          on:click={openOnLichess}
          class="w-full py-4 px-6 bg-white text-neutral-900 font-medium rounded-xl transition-all active:scale-[0.98] active:bg-neutral-200"
        >
          Open on Lichess
        </button>
        <button
          on:click={resetToStart}
          class="w-full py-4 px-6 bg-neutral-900 border border-neutral-800 text-neutral-300 font-medium rounded-xl transition-all active:scale-[0.98] active:bg-neutral-800"
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
</style>

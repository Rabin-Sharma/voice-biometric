const Recorder = (() => {
  const targetRate = 16000;

  function flattenBuffers(buffers) {
    const length = buffers.reduce((sum, buffer) => sum + buffer.length, 0);
    const result = new Float32Array(length);
    let offset = 0;
    buffers.forEach((buffer) => {
      result.set(buffer, offset);
      offset += buffer.length;
    });
    return result;
  }

  function downsampleBuffer(buffer, sampleRate, outRate) {
    if (outRate === sampleRate) {
      return buffer;
    }
    const ratio = sampleRate / outRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offset = 0;
    for (let i = 0; i < newLength; i++) {
      const start = Math.round(i * ratio);
      const end = Math.round((i + 1) * ratio);
      let sum = 0;
      let count = 0;
      for (let j = start; j < end && j < buffer.length; j++) {
        sum += buffer[j];
        count += 1;
      }
      result[offset] = sum / Math.max(1, count);
      offset += 1;
    }
    return result;
  }

  function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }

    return new Blob([view], { type: "audio/wav" });
  }

  function drawWaveform(canvas, analyser, stopFlag) {
    const ctx = canvas.getContext("2d");
    const data = new Uint8Array(analyser.fftSize);

    const render = () => {
      if (stopFlag.stopped) {
        return;
      }
      analyser.getByteTimeDomainData(data);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "rgba(214, 179, 106, 0.8)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      const slice = canvas.width / data.length;
      data.forEach((value, index) => {
        const x = index * slice;
        const y = (value / 255) * canvas.height;
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
      requestAnimationFrame(render);
    };
    render();
  }

  async function recordWav({
    durationMs = 6000,
    minDurationMs = 1500,
    silenceDurationMs = 1200,
    silenceThreshold = 0.01,
    canvas,
  }) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;

    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    const buffers = [];
    const startTime = performance.now();
    let lastVoiceTime = startTime;
    let stopped = false;

    source.connect(analyser);
    analyser.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      buffers.push(new Float32Array(input));
      let sum = 0;
      for (let i = 0; i < input.length; i++) {
        sum += input[i] * input[i];
      }
      const rms = Math.sqrt(sum / input.length);
      if (rms >= silenceThreshold) {
        lastVoiceTime = performance.now();
      }
    };

    const stopFlag = { stopped: false };
    if (canvas) {
      drawWaveform(canvas, analyser, stopFlag);
    }

    await new Promise((resolve) => {
      const checkStop = () => {
        if (stopped) {
          return;
        }
        const now = performance.now();
        const elapsed = now - startTime;
        const silenceElapsed = now - lastVoiceTime;
        const shouldStop =
          elapsed >= durationMs ||
          (elapsed >= minDurationMs && silenceElapsed >= silenceDurationMs);
        if (shouldStop) {
          stopped = true;
          stopFlag.stopped = true;
          processor.disconnect();
          analyser.disconnect();
          source.disconnect();
          stream.getTracks().forEach((track) => track.stop());
          audioContext.close().then(resolve);
          return;
        }
        setTimeout(checkStop, 100);
      };
      setTimeout(checkStop, 100);
    });

    const merged = flattenBuffers(buffers);
    const downsampled = downsampleBuffer(merged, audioContext.sampleRate, targetRate);
    return encodeWav(downsampled, targetRate);
  }

  return { recordWav };
})();

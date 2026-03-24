import React, { useRef, useEffect } from 'react';

/**
 * DarkVeil — A WebGL-powered animated dark background effect.
 * Creates a deep, moody atmosphere with flowing gradient orbs,
 * subtle noise, and organic motion.
 */
interface DarkVeilProps {
  speed?: number;
  noiseIntensity?: number;
  hueShift?: number;
  resolutionScale?: number;
}

const VERTEX_SHADER = `
  attribute vec2 a_position;
  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  precision mediump float;
  uniform float u_time;
  uniform vec2 u_resolution;
  uniform float u_speed;
  uniform float u_noiseIntensity;
  uniform float u_hueShift;

  // Simplex-like noise
  vec3 mod289(vec3 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
  vec2 mod289(vec2 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
  vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

  float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                       -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                             + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
                            dot(x12.zw,x12.zw)), 0.0);
    m = m * m;
    m = m * m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
    vec3 g;
    g.x = a0.x * x0.x + h.x * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float t = u_time * u_speed;

    // Rich dark base — slightly brighter to avoid pure black
    vec3 baseColor = vec3(0.045, 0.05, 0.1);

    // Flowing gradient orbs — more pronounced
    float n1 = snoise(uv * 2.0 + vec2(t * 0.15, t * 0.1)) * 0.5 + 0.5;
    float n2 = snoise(uv * 3.0 - vec2(t * 0.12, t * 0.08)) * 0.5 + 0.5;
    float n3 = snoise(uv * 1.5 + vec2(t * 0.08, -t * 0.13)) * 0.5 + 0.5;
    float n4 = snoise(uv * 4.0 + vec2(-t * 0.1, t * 0.18)) * 0.5 + 0.5;

    // Brighter, more vivid color gradients
    vec3 color1 = hsv2rgb(vec3(0.68 + u_hueShift, 0.8, 0.35));  // Bright indigo
    vec3 color2 = hsv2rgb(vec3(0.75 + u_hueShift, 0.75, 0.30)); // Vivid violet
    vec3 color3 = hsv2rgb(vec3(0.52 + u_hueShift, 0.65, 0.25)); // Teal/cyan
    vec3 color4 = hsv2rgb(vec3(0.58 + u_hueShift, 0.6, 0.20));  // Blue accent

    vec3 gradient = color1 * n1 * 0.7 + color2 * n2 * 0.55 + color3 * n3 * 0.45 + color4 * n4 * 0.3;

    // Soft radial glow in center
    float centerGlow = 1.0 - length((uv - vec2(0.5, 0.4)) * vec2(1.3, 1.6));
    centerGlow = smoothstep(0.0, 0.7, centerGlow) * 0.15;
    gradient += vec3(0.15, 0.1, 0.35) * centerGlow;

    // Gentle vignette
    float vignette = 1.0 - length((uv - 0.5) * 1.4);
    vignette = smoothstep(0.0, 0.85, vignette);

    // Fine grain noise
    float grain = snoise(gl_FragCoord.xy * 0.8 + t * 10.0) * u_noiseIntensity * 0.025;

    vec3 finalColor = baseColor + gradient * vignette + grain;

    // Allow richer color range
    finalColor = clamp(finalColor, 0.0, 0.35);

    gl_FragColor = vec4(finalColor, 1.0);
  }
`;

const DarkVeil: React.FC<DarkVeilProps> = ({
  speed = 0.5,
  noiseIntensity = 0.3,
  hueShift = 0,
  resolutionScale = 0.5,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl', {
      alpha: false,
      antialias: false,
      preserveDrawingBuffer: false,
    });
    if (!gl) return;

    // Create shaders
    const vs = gl.createShader(gl.VERTEX_SHADER)!;
    gl.shaderSource(vs, VERTEX_SHADER);
    gl.compileShader(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER)!;
    gl.shaderSource(fs, FRAGMENT_SHADER);
    gl.compileShader(fs);

    const program = gl.createProgram()!;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    gl.useProgram(program);

    // Full-screen quad
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW
    );
    const posLoc = gl.getAttribLocation(program, 'a_position');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    // Uniforms
    const uTime = gl.getUniformLocation(program, 'u_time');
    const uRes = gl.getUniformLocation(program, 'u_resolution');
    const uSpeed = gl.getUniformLocation(program, 'u_speed');
    const uNoise = gl.getUniformLocation(program, 'u_noiseIntensity');
    const uHue = gl.getUniformLocation(program, 'u_hueShift');

    gl.uniform1f(uSpeed, speed);
    gl.uniform1f(uNoise, noiseIntensity);
    gl.uniform1f(uHue, hueShift);

    const handleResize = () => {
      const w = Math.floor(window.innerWidth * resolutionScale);
      const h = Math.floor(window.innerHeight * resolutionScale);
      canvas.width = w;
      canvas.height = h;
      canvas.style.width = '100vw';
      canvas.style.height = '100vh';
      gl.viewport(0, 0, w, h);
      gl.uniform2f(uRes, w, h);
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const startTime = performance.now();

    const render = () => {
      const elapsed = (performance.now() - startTime) / 1000;
      gl.uniform1f(uTime, elapsed);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      animationRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationRef.current);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      gl.deleteBuffer(buffer);
    };
  }, [speed, noiseIntensity, hueShift, resolutionScale]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
};

export default DarkVeil;

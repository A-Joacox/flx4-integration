// Julia set con modos de animacion. Uniforms alimentados por OSC (bridge/bridge.py):
//   uMode: 0 manual, 1 morph, 2 tunel, 3 viaje, 4 caleidoscopio, 5 neon
//   uBass/uMid/uTreble (0-1) y uBeat (flash que decae) vienen del analyzer.
#version 460 core

out vec4 fragColor;

uniform vec2  uResolution;
uniform float uTime;
uniform vec2  uC;
uniform float uZoom;
uniform vec2  uOffset;
uniform int   uIterations;
uniform float uHueShift;
uniform float uBeat;
uniform int   uMode;
uniform float uTravel;
uniform float uBass;
uniform float uMid;
uniform float uTreble;

const float TUNNEL_SPAN = 1.2;
const float TUNNEL_TWIST = 0.35;

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

// iteracion julia. Devuelve:
//   .x = conteo suave de iteraciones ABSOLUTO (no dividido por maxIter: asi el
//        color no se lava cuando las iteraciones suben en zooms profundos)
//   .y = orbit trap (distancia minima de la orbita a un circulo) para el modo neon
//   .x < 0 -> interior del conjunto
vec2 juliaOrbit(vec2 z, vec2 c, int maxIter) {
    float trap = 1e9;
    float m2 = 0.0;
    int i;
    for (i = 0; i < maxIter; ++i) {
        z = vec2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
        m2 = dot(z, z);
        trap = min(trap, abs(length(z) - 0.5));
        if (m2 > 256.0) break;
    }
    if (i >= maxIter) return vec2(-1.0, trap);
    float si = float(i) - log2(log2(m2)) + 4.0;  // smooth iteration count
    return vec2(si, trap);
}

void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - uResolution) / uResolution.y;
    vec2 z;
    float glow = 0.0;

    if (uMode == 4) {
        // caleidoscopio: plegar el angulo en N sectores espejados, rotando lento
        float r = length(uv);
        float a = atan(uv.y, uv.x) + uTime * (0.05 + 0.10 * uMid);
        float N = 8.0;
        float seg = 6.2831853 / N;
        a = abs(mod(a, seg) - seg * 0.5);
        uv = r * vec2(cos(a), sin(a));
    }

    if (uMode == 2) {
        // tunel: mapeo log-polar con repeticion -> zoom infinito
        vec2 p = uv / uZoom + uOffset;
        float r = max(length(p), 1e-6);
        float ang = atan(p.y, p.x) + TUNNEL_TWIST * uTravel;
        float depth = mod(log(r) - uTravel, TUNNEL_SPAN);
        float rr = exp(depth - TUNNEL_SPAN * 0.5);
        z = rr * vec2(cos(ang), sin(ang));
        glow = smoothstep(0.35, 0.0, r) * (0.35 + 0.4 * uBass);
        z += uTreble * 0.02 * vec2(sin(40.0 * ang + uTime * 3.0), cos(36.0 * ang - uTime * 2.0));
    } else {
        z = uv / uZoom + uOffset;
        z += uTreble * 0.015 * vec2(sin(30.0 * z.y + uTime * 4.0), sin(30.0 * z.x - uTime * 3.0));
    }

    vec2 res = juliaOrbit(z, uC, uIterations);
    float si = res.x;
    float trap = res.y;
    bool inside = si < 0.0;

    vec3 col;
    if (uMode == 5) {
        // neon: filamentos por orbit trap sobre fondo negro
        float line = exp(-trap * (7.0 + 6.0 * uTreble));
        float hue = fract(si * 0.004 + uHueShift + 0.12 * uMid + 0.05 * uTime * 0.2);
        if (inside) hue = fract(uHueShift + 0.6);
        float intensity = line * (0.75 + 0.6 * uBass);
        col = hsv2rgb(vec3(hue, 0.9, 1.0)) * intensity;
        col += hsv2rgb(vec3(fract(hue + 0.5), 0.6, 1.0)) * exp(-trap * 30.0) * 0.6;  // nucleo blanco-frio
    } else {
        // coloreado estandar: hue por conteo absoluto (estable a cualquier profundidad;
        // /200 mantiene el look historico con iter=200)
        float hue = fract(si * (0.9 + 0.3 * uMid) / 200.0 + uHueShift + 0.15 * uMid);
        float sat = 0.75 + 0.2 * uBass;
        float f = inside ? 1.0 : clamp(si / float(uIterations), 0.0, 1.0);
        float val = inside ? 0.0 : pow(f, 0.45);
        val = clamp(val * (0.85 + 0.5 * uBass) + glow, 0.0, 1.3);
        col = hsv2rgb(vec3(hue, sat, min(val, 1.0)));
        col += glow * vec3(0.9, 0.7, 1.0) * 0.3;
    }

    col += uBeat * vec3(0.35, 0.30, 0.45);
    fragColor = vec4(col, 1.0);
}

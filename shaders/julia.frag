// Julia set con modos de animacion. Uniforms pensados para OSC (Fase 4):
//   uMode: 0=manual, 1=morph (c orbita solo), 2=tunel (zoom infinito log-polar)
//   uBass/uMid/uTreble (0-1) y uBeat (flash que decae) vienen del analyzer.
#version 460 core

out vec4 fragColor;

uniform vec2  uResolution;
uniform float uTime;
uniform vec2  uC;          // parametro c (manual o autopilot desde C++)
uniform float uZoom;
uniform vec2  uOffset;
uniform int   uIterations;
uniform float uHueShift;
uniform float uBeat;       // 0-1, decae
uniform int   uMode;       // 0 manual, 1 morph, 2 tunel
uniform float uTravel;     // profundidad del tunel (crece con el tiempo/bass)
uniform float uBass;
uniform float uMid;
uniform float uTreble;

const float TUNNEL_SPAN = 1.2;   // periodo en log-espacio (auto-similitud)
const float TUNNEL_TWIST = 0.35; // rotacion por unidad de travel

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

// iteracion julia con conteo suave (elimina banding entre iteraciones)
float julia(vec2 z, vec2 c, int maxIter) {
    float m2 = 0.0;
    int i;
    for (i = 0; i < maxIter; ++i) {
        z = vec2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
        m2 = dot(z, z);
        if (m2 > 256.0) break;
    }
    if (i >= maxIter) return 1.0;
    // smooth iteration count
    return (float(i) - log2(log2(m2)) + 4.0) / float(maxIter);
}

void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - uResolution) / uResolution.y;
    vec2 c = uC;
    vec2 z;
    float glow = 0.0;

    if (uMode == 2) {
        // ---- tunel: mapeo log-polar con repeticion -> zoom infinito ----
        vec2 p = uv / uZoom + uOffset;
        float r = max(length(p), 1e-6);
        float ang = atan(p.y, p.x) + TUNNEL_TWIST * uTravel;
        // profundidad en log-espacio, desplazada por travel y repetida
        float depth = mod(log(r) - uTravel, TUNNEL_SPAN);
        float rr = exp(depth - TUNNEL_SPAN * 0.5);  // centrado en el periodo
        z = rr * vec2(cos(ang), sin(ang));
        // luz al fondo del tunel
        glow = smoothstep(0.35, 0.0, r) * (0.35 + 0.4 * uBass);
        // el treble "ensucia" los bordes del tunel
        z += uTreble * 0.02 * vec2(sin(40.0 * ang + uTime * 3.0), cos(36.0 * ang - uTime * 2.0));
    } else {
        z = uv / uZoom + uOffset;
        z += uTreble * 0.015 * vec2(sin(30.0 * z.y + uTime * 4.0), sin(30.0 * z.x - uTime * 3.0));
    }

    float f = julia(z, c, uIterations);

    float hue = fract(f * (0.9 + 0.3 * uMid) + uHueShift + 0.15 * uMid);
    float sat = 0.75 + 0.2 * uBass;
    float val = (f >= 1.0) ? 0.0 : pow(clamp(f, 0.0, 1.0), 0.45);
    // el bass empuja el brillo general; el beat mete flash
    val = clamp(val * (0.85 + 0.5 * uBass) + glow, 0.0, 1.3);

    vec3 col = hsv2rgb(vec3(hue, sat, min(val, 1.0)));
    col += uBeat * vec3(0.35, 0.30, 0.45);   // flash frio en el beat
    col += glow * vec3(0.9, 0.7, 1.0) * 0.3;

    fragColor = vec4(col, 1.0);
}

// Fase 3: fragment shader base — Julia set parametrizable.
// Uniforms pensados para recibir valores vía OSC en Fase 4/5.
#version 460 core

out vec4 fragColor;

uniform vec2  uResolution;
uniform float uTime;
uniform vec2  uC;          // parámetro c del Julia set (MIDI: knobs)
uniform float uZoom;       // MIDI/bass
uniform vec2  uOffset;     // MIDI: jog wheel
uniform int   uIterations; // MIDI
uniform float uHueShift;   // audio: mid
uniform float uBeat;       // audio: beat flash (0-1, decae)

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - uResolution) / uResolution.y;
    vec2 z = uv / uZoom + uOffset;

    int i;
    for (i = 0; i < uIterations; ++i) {
        z = vec2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + uC;
        if (dot(z, z) > 4.0) break;
    }

    float f = float(i) / float(uIterations);
    vec3 col = hsv2rgb(vec3(fract(f + uHueShift), 0.8, f < 1.0 ? pow(f, 0.5) : 0.0));
    col += uBeat * 0.3; // flash en beat
    fragColor = vec4(col, 1.0);
}

"""Voices of the channel's intro Short (content/especiales/presentacion/lineas.json) -> voces/<id>.mp3 + duraciones.json,
and the other versions tried, to compare, in voces-pruebas/<version>/. Same voices as src/voice.mjs (edge-tts, silence
trimmed at both ends); the main version no longer has the pitch / formant child processing.
Usage: python3 tools/presentacion_voces.py [especial]   (needs edge-tts and ffmpeg; runs in .github/workflows/presentacion-voces.yml)
  especial: a folder of content/especiales (default presentacion); other than the intro, only the main version"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECIAL = sys.argv[1] if len(sys.argv) > 1 else 'presentacion'
DIR = os.path.join(ROOT, 'content/especiales', SPECIAL)
# kid: 1 = no pitch / formant processing afterwards. Chiño found the Rubber Band child voice metallic (2026-10-27):
# the voices now stay as the service speaks them, made a little younger only with its own pitch and rate
VARIANTS = {
    'natural': {'e': {'voice': 'es-ES-XimenaNeural', 'rate': '+4%', 'pitch': '+12Hz', 'kid': 1},
                'r': {'voice': 'es-ES-ElviraNeural', 'rate': '-2%', 'pitch': '+6Hz', 'kid': 1}},
    'sin-tocar': {'e': {'voice': 'es-ES-XimenaNeural', 'rate': '+0%', 'pitch': '+0Hz', 'kid': 1},
                  'r': {'voice': 'es-ES-ElviraNeural', 'rate': '+0%', 'pitch': '+0Hz', 'kid': 1}},
    'metalica-antes': {'e': {'voice': 'es-ES-XimenaNeural', 'rate': '+6%', 'pitch': '+20Hz', 'kid': 1.14},
                       'r': {'voice': 'es-ES-ElviraNeural', 'rate': '-4%', 'pitch': '+10Hz', 'kid': 1.1}},
}
MAIN = 'natural'
SOFT = 'highshelf=f=5500:g=-4,equalizer=f=250:t=q:w=1.2:g=1.5'


def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *args], check=True, capture_output=True)


def probe(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                check=True, capture_output=True, text=True).stdout.strip())


def childify(src, dst, k):
    """k = 1: the voice as the service speaks it. Otherwise the old child voice (pitch and formants up together)."""
    if k == 1:
        ff('-i', src, '-c:a', 'libmp3lame', '-q:a', '0', dst)
        return
    try:
        ff('-i', src, '-af', f'rubberband=pitch={k}:pitchq=quality:formant=shifted:transients=smooth:phase=laminar:window=long,{SOFT}',
           '-c:a', 'libmp3lame', '-q:a', '0', dst)
    except subprocess.CalledProcessError:
        ff('-i', src, '-af', f'asetrate={int(24000 * k)},aresample=24000,atempo={1 / k:.4f},{SOFT}',
           '-c:a', 'libmp3lame', '-q:a', '0', dst)


def multilingual():
    """Spanish (Spain) multilingual voices, the most expressive ones, if the service has them."""
    names = subprocess.run(['edge-tts', '--list-voices'], capture_output=True, text=True).stdout
    found = sorted({w for w in names.split() if w.startswith('es-ES-') and 'Multilingual' in w})
    with open(os.path.join(DIR, 'voces-pruebas', 'voces-disponibles.txt'), 'w') as f:
        f.write(names)
    fem = [n for n in found if any(k in n for k in ('Ximena', 'Arabella', 'Isidora', 'Elvira'))]
    if len(fem) >= 2:
        VARIANTS['multilingue'] = {'e': {'voice': fem[0], 'rate': '+4%', 'pitch': '+10Hz', 'kid': 1},
                                   'r': {'voice': fem[1], 'rate': '-2%', 'pitch': '+5Hz', 'kid': 1}}


def main():
    if SPECIAL != 'presentacion':
        render(MAIN, os.path.join(DIR, 'voces'))
        return
    os.makedirs(os.path.join(DIR, 'voces-pruebas'), exist_ok=True)
    multilingual()
    for name in VARIANTS:
        render(name, os.path.join(DIR, 'voces') if name == MAIN else os.path.join(DIR, 'voces-pruebas', name))


def render(name, out):
    lines = json.load(open(os.path.join(DIR, 'lineas.json')))['lineas']
    os.makedirs(out, exist_ok=True)
    durs = {}
    for ln in lines:
        v = VARIANTS[name][ln['who']]
        raw, trim, dst = f'/tmp/{ln["id"]}.mp3', f'/tmp/{ln["id"]}.trim.wav', os.path.join(out, ln['id'] + '.mp3')
        subprocess.run(['edge-tts', '--voice', v['voice'], f'--rate={v["rate"]}', f'--pitch={v["pitch"]}',
                        '--text', ln['text'], '--write-media', raw], check=True)
        sr = 'silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04'
        ff('-i', raw, '-af', f'{sr},areverse,{sr.replace("0.04", "0.12")},areverse', trim)
        childify(trim, dst, v['kid'])
        durs[ln['id']] = round(probe(dst), 3)
        print(name, ln['id'], ln['who'], v['voice'], durs[ln['id']], ln['text'])
    json.dump(durs, open(os.path.join(out, 'duraciones.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

"""Voices of the channel's intro Short (content/especiales/presentacion/lineas.json) -> voces/<id>.mp3 + duraciones.json.
Same voices and child processing as src/voice.mjs (claude/poses): edge-tts, silence trimmed at both ends, then pitch
and formants up together with Rubber Band in quality mode, and a soft high shelf against the metallic shine.
Usage: python3 tools/presentacion_voces.py   (needs edge-tts and ffmpeg; runs in .github/workflows/presentacion-voces.yml)"""
import json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'content/especiales/presentacion')
VOICES = {
    'e': {'voice': 'es-ES-XimenaNeural', 'rate': '+6%', 'pitch': '+20Hz', 'kid': 1.14},
    'r': {'voice': 'es-ES-ElviraNeural', 'rate': '-4%', 'pitch': '+10Hz', 'kid': 1.1},
}
SOFT = 'highshelf=f=5500:g=-4,equalizer=f=250:t=q:w=1.2:g=1.5'


def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *args], check=True, capture_output=True)


def probe(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                check=True, capture_output=True, text=True).stdout.strip())


def main():
    lines = json.load(open(os.path.join(DIR, 'lineas.json')))['lineas']
    out = os.path.join(DIR, 'voces')
    os.makedirs(out, exist_ok=True)
    durs = {}
    for ln in lines:
        v = VOICES[ln['who']]
        raw, trim, dst = f'/tmp/{ln["id"]}.mp3', f'/tmp/{ln["id"]}.trim.wav', os.path.join(out, ln['id'] + '.mp3')
        subprocess.run(['edge-tts', '--voice', v['voice'], f'--rate={v["rate"]}', f'--pitch={v["pitch"]}',
                        '--text', ln['text'], '--write-media', raw], check=True)
        sr = 'silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04'
        ff('-i', raw, '-af', f'{sr},areverse,{sr.replace("0.04", "0.12")},areverse', trim)
        k = v['kid']
        try:
            ff('-i', trim, '-af', f'rubberband=pitch={k}:pitchq=quality:formant=shifted:transients=smooth:phase=laminar:window=long,{SOFT}',
               '-c:a', 'libmp3lame', '-q:a', '0', dst)
        except subprocess.CalledProcessError:
            ff('-i', trim, '-af', f'asetrate={int(24000 * k)},aresample=24000,atempo={1 / k:.4f},{SOFT}',
               '-c:a', 'libmp3lame', '-q:a', '0', dst)
        durs[ln['id']] = round(probe(dst), 3)
        print(ln['id'], ln['who'], durs[ln['id']], ln['text'])
    json.dump(durs, open(os.path.join(out, 'duraciones.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

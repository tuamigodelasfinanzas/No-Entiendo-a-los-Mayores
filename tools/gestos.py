"""Real human gestures for E and R: a recording becomes a "gesto" (gestos/<name>.json), the 3D positions of the
body's joints frame by frame, which tools/malla.py turns into the kids' movement (retarget()).

Sources, both free:
  python3 tools/gestos.py video clip.mp4 nombre [inicio fin]    a phone video of a person doing the gesture, facing the
                                                                camera, whole body or at least from the knees up
                                                                (MediaPipe Pose, runs on this machine)
  python3 tools/gestos.py bvh clip.bvh nombre [inicio fin]      a motion capture file (BVH), e.g. the CMU Graphics Lab
                                                                database (free, commercial use allowed)

Joints, in metres: nose, head (top), neck, shoulder/elbow/wrist/hip/knee/ankle _l/_r (the person's own left and
right). The person faces the camera (face_camera): x to the screen's right (the person's left), y up, z towards
the camera, feet on y = 0.
Needs: pip install mediapipe opencv-python-headless scipy (and libegl1 on Linux)."""
import json, math, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'assets/gestos')
NAMES = ['head', 'nose', 'neck', 'shoulder_l', 'elbow_l', 'wrist_l', 'shoulder_r', 'elbow_r', 'wrist_r',
         'hip_l', 'knee_l', 'ankle_l', 'hip_r', 'knee_r', 'ankle_r']


# ---------------------------------------------------------------- BVH (motion capture)
def read_bvh(path):
    toks = open(path).read().split()
    joints, stack, i = [], [], 0
    while toks[i] != 'MOTION':
        t = toks[i]
        if t in ('ROOT', 'JOINT') or (t == 'End' and toks[i + 1] == 'Site'):
            name = toks[i + 1] if t != 'End' else stack[-1] + '_end'
            joints.append({'name': name, 'parent': stack[-1] if stack else None, 'ch': [], 'off': None})
            i += 2
        elif t == '{':
            stack.append(joints[-1]['name'])
            i += 1
        elif t == '}':
            stack.pop()
            i += 1
        elif t == 'OFFSET':
            joints[-1]['off'] = np.array([float(x) for x in toks[i + 1:i + 4]])
            i += 4
        elif t == 'CHANNELS':
            n = int(toks[i + 1])
            joints[-1]['ch'] = toks[i + 2:i + 2 + n]
            i += 2 + n
        else:
            i += 1
    n = int(toks[i + 2])
    dt = float(toks[i + 5])
    data = np.array(toks[i + 6:], float).reshape(n, -1)
    return joints, dt, data


def rot(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == 'X':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'Y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def bvh_positions(path):
    """World positions of every joint, frame by frame: {name: (n, 3)}, and the frame time."""
    joints, dt, data = read_bvh(path)
    out = {j['name']: np.zeros((len(data), 3)) for j in joints}
    for f, row in enumerate(data):
        k, G = 0, {}
        for j in joints:
            R, p = np.eye(3), np.zeros(3)
            for ch in j['ch']:
                v = row[k]
                k += 1
                if ch.endswith('position'):
                    p['XYZ'.index(ch[0])] = v
                else:
                    R = R @ rot(ch[0], v)
            if j['parent'] is None:
                G[j['name']] = (R, p + j['off'])
            else:
                PR, Pp = G[j['parent']]
                G[j['name']] = (PR @ R, Pp + PR @ j['off'])
            out[j['name']][f] = G[j['name']][1]
    return out, dt


CMU = {'head': 'Head_end', 'nose': 'Head', 'neck': 'Neck1', 'shoulder_l': 'LeftArm', 'elbow_l': 'LeftForeArm',
       'wrist_l': 'LeftHand', 'shoulder_r': 'RightArm', 'elbow_r': 'RightForeArm', 'wrist_r': 'RightHand',
       'hip_l': 'LeftUpLeg', 'knee_l': 'LeftLeg', 'ankle_l': 'LeftFoot', 'hip_r': 'RightUpLeg', 'knee_r': 'RightLeg',
       'ankle_r': 'RightFoot'}


def from_bvh(path):
    P, dt = bvh_positions(path)
    X = np.stack([P[CMU[n]] for n in NAMES], 1) * 0.0254 * 2.3      # CMU BVH units -> metres (about)
    return X[1:], 1 / dt                                              # frame 0 is the T pose of the conversion


# ---------------------------------------------------------------- video (MediaPipe Pose)
MP_MODEL = os.environ.get('POSE_MODEL', os.path.join(ROOT, 'out/pose_landmarker_heavy.task'))
MP_URL = ('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/'
          'pose_landmarker_heavy.task')
MP = {'nose': 0, 'shoulder_l': 11, 'shoulder_r': 12, 'elbow_l': 13, 'elbow_r': 14, 'wrist_l': 15, 'wrist_r': 16,
      'hip_l': 23, 'hip_r': 24, 'knee_l': 25, 'knee_r': 26, 'ankle_l': 27, 'ankle_r': 28, 'ear_l': 7, 'ear_r': 8}


def from_video(path):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    if not os.path.exists(MP_MODEL):
        import urllib.request
        os.makedirs(os.path.dirname(MP_MODEL), exist_ok=True)
        urllib.request.urlretrieve(MP_URL, MP_MODEL)
    opts = vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=MP_MODEL),
                                        running_mode=vision.RunningMode.VIDEO, num_poses=1)
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frames, last = [], None
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        i = 0
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            r = lm.detect_for_video(img, int(i * 1000 / fps))
            i += 1
            if r.pose_world_landmarks:
                w = r.pose_world_landmarks[0]
                # MediaPipe: x to the image's right, y down, z away from the camera (metres, centred on the hips)
                q = {n: np.array([-w[k].x, -w[k].y, -w[k].z]) for n, k in MP.items()}
                q['neck'] = (q['shoulder_l'] + q['shoulder_r']) / 2
                ear = (q['ear_l'] + q['ear_r']) / 2
                q['head'] = ear + (ear - q['neck']) * 0.9
                last = np.stack([q[n] for n in NAMES])
            frames.append(last)
    first = next(f for f in frames if f is not None)
    X = np.stack([f if f is not None else first for f in frames])
    return X, fps


# ---------------------------------------------------------------- common
def face_camera(X):
    """Turns the whole clip so that, on average, the person faces the camera (+z) and stands on y = 0, with the
    hips centred at x = 0 on the first frame."""
    i = {n: k for k, n in enumerate(NAMES)}
    sh = (X[:, i['shoulder_l']] - X[:, i['shoulder_r']]).mean(0) + (X[:, i['hip_l']] - X[:, i['hip_r']]).mean(0)
    a = math.atan2(sh[2], sh[0])           # the person's left should point along +x (their left = screen right)
    c, s = math.cos(a), math.sin(a)
    Ry = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    X = X @ Ry.T
    hips = (X[0, i['hip_l']] + X[0, i['hip_r']]) / 2
    X = X - np.array([hips[0], 0, hips[2]])
    X[..., 1] -= min(X[:, i['ankle_l'], 1].min(), X[:, i['ankle_r'], 1].min())
    return X


def smooth(X, fps, cutoff=6.0):
    """Low-pass (Gaussian, about cutoff Hz) so trembling of the capture doesn't show; gestures keep their timing."""
    from scipy.ndimage import gaussian_filter1d
    sigma = fps / (2 * math.pi * cutoff)
    return gaussian_filter1d(X, sigma, axis=0, mode='nearest')


def resample(X, fps, out_fps=30):
    n = int(len(X) / fps * out_fps)
    t = np.arange(n) / out_fps * fps
    k = np.clip(t.astype(int), 0, len(X) - 2)
    f = (t - k)[:, None, None]
    return X[k] * (1 - f) + X[k + 1] * f


def save(name, X, fps, a=None, b=None, source=''):
    X = smooth(X, fps)
    X = resample(X, fps)
    X = X[int((a or 0) * 30): int(b * 30) if b else None]
    X = face_camera(X)
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, name + '.json')
    json.dump({'fps': 30, 'source': source, 'joints': NAMES, 'frames': np.round(X, 4).tolist()}, open(path, 'w'))
    return path


def load(name):
    g = json.load(open(os.path.join(DIR, name + '.json')))
    return np.array(g['frames']), g['fps']


if __name__ == '__main__':
    kind, src, name = sys.argv[1:4]
    a, b = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (None, None)
    X, fps = from_bvh(src) if kind == 'bvh' else from_video(src)
    print(save(name, X, fps, a, b, os.path.basename(src)), len(X) / fps, 's')

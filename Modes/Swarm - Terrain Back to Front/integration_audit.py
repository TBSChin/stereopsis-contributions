"""On-device, isolated native-renderer regression and transition audit."""
import ctypes as C
import json
import math
import os
import threading
import time


def bind(path):
    lib = C.CDLL(path)
    F = C.POINTER(C.c_float)
    lib.sw_frame.argtypes = [C.c_void_p] + [C.c_int] * 7 + [F, C.c_int, C.c_int,
        F, C.c_int, C.c_int, C.c_void_p, C.c_int, C.c_float, C.c_void_p, C.c_int, F]
    lib.sw_debug.argtypes = [F, C.c_int]
    lib.sw_threads(1)
    return lib


def buffers():
    w, h = 128, 96
    return ((C.c_uint32 * (w*h))(), (C.c_float * (w*h*3))(),
            (C.c_float * (((w+3)//4)*((h+3)//4)*6))())


def render(lib, buf, params, fft, wave):
    dst, acc, bloom = buf
    rc = lib.sw_frame(dst, 128, 96, 128*4, 1, 16, 8, 0, acc, 128, 96,
                      bloom, 32, 24, fft, 1024, 15.625, wave, 1024, params)
    if rc:
        raise RuntimeError('sw_frame rc=%d' % rc)
    return bytes(dst)


def debug(lib):
    values = (C.c_float * 8)()
    lib.sw_debug(values, 8)
    return list(values)


def run(root, build, getter):
    report = {'started': time.time(), 'stock': [], 'transitions': [], 'ok': False}
    path = os.path.join(root, 'shared-audit-report.json')
    try:
        print('[shared-audit] starting isolated comparison', flush=True)
        stock_so = '/sdcard/Modes/Swarm - Orb/swarm_d00b42a127_armv7l.so'
        a = bind(stock_so if os.path.isfile(stock_so) else build(root, 'audit_baseline.c', 'auditbaseline'))
        optimized = os.path.join(root, 'auditcandidate_armv7.so')
        b = bind(optimized if os.path.isfile(optimized) else build(root, 'audit_candidate.c', 'auditcandidate'))
        fft, wave = (C.c_float * 1024)(), (C.c_float * 1024)()
        for style in range(7):
            for case in range(2):
                a.sw_init(4096, 7)
                b.sw_init(4096, 7)
                ba, bb = buffers(), buffers()
                mismatches = 0
                changed_pixels = max_channel_error = 0
                baseline_seconds = candidate_seconds = 0.0
                for frame in range(45):
                    t = frame / 60.0
                    for k in range(1024):
                        fft[k] = min(1.0, (0.6*math.exp(-k/90.0)+0.08)*(0.7+0.3*math.sin(k*0.03+t*5)))
                        wave[k] = 0.65*math.sin(k*0.06+t*5)
                    quiet = style == 2
                    p = (C.c_float * 33)(1/60.0, style, -0.3 if case else 0.2,
                        0.85 if case else 0.25, 0.37, 0.03, 0.01, 0.02,
                        0.4, 0.3, 0.2, 0.25, (frame % 30)/30.0, float(frame % 30 == 0),
                        float(frame == 20 and not quiet), 4.0, 1.0, 1.5, 1.05, 0.0,
                        0.8 if case else 1.1, 0.4 if style == 5 else 0,
                        0.35 if style == 5 else 0, 14.0,
                        0.0 if quiet else 1.0, 0.0 if quiet else 1.0,
                        0.0 if quiet else 1.0, 1.12 if style == 3 else 1,
                        0.3 if style == 3 else 0, 1.8 if style == 1 else 1,
                        0.2 if style == 3 else 0, 0.65 if style == 5 else 1, 1.3 if style == 6 else 1)
                    before = time.perf_counter()
                    original = render(a, ba, p, fft, wave)
                    baseline_seconds += time.perf_counter() - before
                    before = time.perf_counter()
                    candidate = render(b, bb, p, fft, wave)
                    candidate_seconds += time.perf_counter() - before
                    if original != candidate:
                        mismatches += 1
                        changed_pixels += sum(original[i:i+4] != candidate[i:i+4] for i in range(0, len(original), 4))
                        max_channel_error = max(max_channel_error, max(abs(x-y) for x,y in zip(original,candidate)))
                report['stock'].append({'style': style, 'case': case, 'frames': 45, 'different_frames': mismatches,
                    'changed_pixels': changed_pixels, 'total_pixels': 45*128*96, 'max_channel_error': max_channel_error,
                    'baseline_ms_per_frame': baseline_seconds/45*1000, 'candidate_ms_per_frame': candidate_seconds/45*1000})
                print('[shared-audit] stock %d case %d: %d different frames' % (style, case, mismatches), flush=True)
        b.sw_init(4096, 7)
        bb = buffers()
        p = (C.c_float * 33)(1/60.0, 2, 0, 0.3, 0.2, 0,0,0, .3,.2,.2,.1,0,0,0,4,1,1.5,1.05,0,1,0,0,16,0,0,0,1,0,1,0,1,1)
        render(b, bb, p, fft, wave)
        for style in (8, 2, 5, 7, 3, 9, 6, 10, 1, 4):
            previous = int(debug(b)[0])
            p[1] = style
            render(b, bb, p, fft, wave)
            state = debug(b)
            assert int(state[0]) == style and state[2] == 1.0 and state[1] < .1, state
            for _ in range(100):
                render(b, bb, p, fft, wave)
            assert debug(b)[2] == 0.0
            report['transitions'].append({'from': previous, 'to': style, 'morph_started': True, 'morph_completed': True})
        report['pixel_identical'] = all(x['different_frames'] == 0 for x in report['stock'])
        report['appearance_equivalent'] = all(x['max_channel_error'] <= 2 and
            x['changed_pixels'] / x['total_pixels'] < 0.002 for x in report['stock'])
        report['tolerance'] = 'At most 2/255 channel rounding on less than 0.2 percent of pixels; layouts and params unchanged'
        report['ok'] = report['appearance_equivalent'] and len(report['transitions']) == 10
        report['finished'] = time.time()
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        print('[shared-audit] COMPLETE ok=%s' % report['ok'], flush=True)
    except Exception as exc:
        import traceback
        report['error'] = traceback.format_exc()
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        print('[shared-audit] FAILED %s' % exc, flush=True)
        return
    # Read-only live trace: shows that stock modes drive this exact library's
    # state, and catches reinitialization when a mode joins with a wrong count.
    trace = []
    end = time.time() + 360
    last = None
    while time.time() < end:
        lib = getter()
        if lib is not None:
            st = debug(lib)
            key = (int(st[0]), int(st[2]), int(st[3]))
            if key != last:
                trace.append({'time': time.time(), 'style': st[0], 'morph': st[1],
                              'morphing': st[2], 'transition': st[3], 'count': lib.sw_ready()})
                with open(os.path.join(root, 'shared-live-trace.json'), 'w') as f:
                    json.dump(trace, f, indent=2)
                print('[shared-live] %s' % trace[-1], flush=True)
                last = key
        time.sleep(.05)


def start(root, build, getter):
    flag = os.path.join(root, 'RUN_COMPILER_PROBE')
    if os.path.exists(flag):
        os.remove(flag)
        threading.Thread(target=probe, args=(root,), daemon=True).start()
        return
    threading.Thread(target=run, args=(root, build, getter), daemon=True).start()


def probe(root):
    import glob
    import subprocess
    report = {'attempts': []}
    base = ['-O3', '-fno-math-errno', '-shared', '-fPIC', '-pthread']
    out = os.path.join(root, 'auditcandidate_armv7.so')
    for arch in (['-mcpu=cortex-a7', '-mfpu=neon-vfpv4', '-mfloat-abi=hard', '-funsafe-math-optimizations'],
                 ['-march=armv7ve', '-mfpu=neon-vfpv4', '-mfloat-abi=hard']):
        t0 = time.time()
        r = subprocess.run(['gcc']+base+arch+['-o',out,os.path.join(root,'swarm.c'),'-lm'], capture_output=True,text=True,timeout=180)
        report['attempts'].append(dict(flags=arch, rc=r.returncode, seconds=time.time()-t0, stderr=r.stderr))
        if r.returncode == 0:
            break
    for name, pattern in [('baseline','auditbaseline_*.so'), ('candidate','auditcandidate_c4*.so'), ('armv7','auditcandidate_armv7.so')]:
        paths = glob.glob(os.path.join(root, pattern))
        if paths:
            r = subprocess.run(['readelf','-A',paths[0]], capture_output=True,text=True)
            report[name+'_attributes'] = r.stdout
    if report['attempts'][-1]['rc'] == 0:
        a = bind(glob.glob(os.path.join(root,'auditbaseline_*.so'))[0])
        b = bind(out)
        a.sw_init(4096,7);b.sw_init(4096,7)
        ba,bb=buffers(),buffers()
        fft,wave=(C.c_float*1024)(),(C.c_float*1024)()
        for k in range(1024):
            fft[k]=.5*math.exp(-k/90)+.05;wave[k]=math.sin(k*.05)*.5
        p=(C.c_float*33)(1/60,2,0,.3,.2,0,0,0,.3,.2,.2,.1,0,0,0,4,1,1.5,1.05,0,1,0,0,16,0,0,0,1,0,1,0,1,1)
        ta=tb=0.0
        changed=maxerr=0
        for _ in range(60):
            t=time.perf_counter();aa=render(a,ba,p,fft,wave);ta+=time.perf_counter()-t
            t=time.perf_counter();bbits=render(b,bb,p,fft,wave);tb+=time.perf_counter()-t
            if aa != bbits:
                changed+=sum(aa[i:i+4]!=bbits[i:i+4] for i in range(0,len(aa),4))
                maxerr=max(maxerr,max(abs(x-y) for x,y in zip(aa,bbits)))
        report['benchmark']=dict(baseline_ms=ta/60*1000, candidate_ms=tb/60*1000,changed_pixels=changed,total_pixels=60*128*96,max_channel_error=maxerr)
    with open(os.path.join(root,'compiler-probe.json'),'w') as f:
        json.dump(report,f,indent=2)
    print('[shared-probe] COMPLETE %s' % report.get('benchmark',report['attempts']),flush=True)

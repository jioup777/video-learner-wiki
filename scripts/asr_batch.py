#!/usr/bin/env python3
"""批量ASR：小文件逐段上传转录，绕过大文件SSL问题"""
import os, sys, json, time, glob, requests

API_KEY = os.getenv('DASHSCOPE_API_KEY') or os.getenv('ALIYUN_ASR_API_KEY', 'sk-601abb31fe354b6daf24067c7a56adc6')
BASE = "https://dashscope.aliyuncs.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def upload(path):
    with open(path, 'rb') as f:
        r = requests.post(f"{BASE}/files", headers=HEADERS,
            files={'file': (os.path.basename(path), f)},
            data={'purpose': 'inference'}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"upload fail {r.status_code}: {r.text[:200]}")
    fid = r.json()['data']['uploaded_files'][0]['file_id']
    # get url
    r2 = requests.get(f"{BASE}/files/{fid}", headers=HEADERS, timeout=30)
    return r2.json()['data']['url'], fid

def transcribe(urls):
    r = requests.post(f"{BASE}/services/audio/asr/transcription",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"model": "fun-asr-mtl", "input": {"file_urls": urls}, "parameters": {}},
        timeout=60)
    if r.status_code != 200:
        # try async task API
        r2 = requests.post(f"{BASE}/tasks",
            headers={**HEADERS, "Content-Type": "application/json", "X-DashScope-Async": "enable"},
            json={"model": "fun-asr-mtl", "input": {"file_urls": urls}, "parameters": {}},
            timeout=60)
        if r2.status_code != 200:
            raise RuntimeError(f"transcribe fail: {r.text[:200]} {r2.text[:200]}")
        return r2.json()['output']['task_id']
    return r.json()['output']['task_id']

def wait(tid, max_wait=180):
    for _ in range(max_wait // 5):
        r = requests.get(f"{BASE}/tasks/{tid}", headers=HEADERS, timeout=30)
        out = r.json()['output']
        st = out.get('task_status', '')
        if st == 'SUCCEEDED': return out
        if st == 'FAILED': raise RuntimeError(f"task failed: {out.get('message')}")
        time.sleep(5)
    raise RuntimeError("timeout")

def get_text(result):
    for res in result.get('results', []):
        url = res.get('transcription_url')
        if url:
            r = requests.get(url, timeout=30)
            data = r.json()
            texts = [t['text'] for t in data.get('transcripts', []) if 'text' in t]
            if texts: return '\n'.join(texts)
    return ''

if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "output/seg_*.wav"
    output = sys.argv[2] if len(sys.argv) > 2 else None
    files = sorted(glob.glob(pattern))
    if not files:
        print("No files found"); sys.exit(1)
    
    all_text = []
    for i, f in enumerate(files):
        name = os.path.basename(f)
        print(f"[{i+1}/{len(files)}] {name}...", end=" ", flush=True)
        try:
            url, fid = upload(f)
            tid = transcribe([url])
            result = wait(tid)
            text = get_text(result)
            all_text.append(text)
            print(f"OK ({len(text)} chars)")
            # cleanup
            try: requests.delete(f"{BASE}/files/{fid}", headers=HEADERS, timeout=10)
            except: pass
        except Exception as e:
            print(f"FAIL: {e}")
            all_text.append("")
    
    combined = '\n'.join(all_text)
    print(f"\n[DONE] Total: {len(combined)} chars")
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(combined)
        print(f"Saved: {output}")
    else:
        print(combined)

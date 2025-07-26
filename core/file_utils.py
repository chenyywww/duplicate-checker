import os
import re
from difflib import SequenceMatcher

def extract_ignore_keywords(raw_input):
    return re.findall(r'[【\(\[]([^\)\]\u3011]+)[\)\]\u3011]', raw_input)

def normalize(name):
    name = re.sub(r'[\\/]', '', name)
    name = re.sub(r'[\(\[].*?[\)\]]', '', name)
    name = re.sub(r'(DL版|パッケージ版|多国語版|files|canplay|Chinese|English|Espanol)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[第]?[一二三四五六七八九十0-9]+[話章部巻代]', '', name)
    name = re.sub(r'[\d]{6,}', '', name)
    name = re.sub(r'\.[a-zA-Z0-9]+$', '', name)
    name = re.sub(r'[\s\-・_]+', '', name)
    return name.strip().lower()

def is_version_variant(a, b, user_keywords):
    version_patterns = [
        r'外传\d+', r'外传[一二三四五六七八九十]', r'vol\.?\s*\d+',
        r'episode\s*\d+', r'ep\s*\d+', r'part\s*\d+',
        r'CASE\.?\s*\d+', r'\b\d+\s*th\b', r'\d+\.\d+',
        r'[一二三四五六七八九十]+$'
    ] + [re.escape(k) for k in user_keywords]
    return any(re.search(p, a, re.IGNORECASE) and re.search(p, b, re.IGNORECASE) for p in version_patterns)

def collect_files(folder, max_depth, progress_callback=None):
    result = []
    base_depth = folder.rstrip(os.sep).count(os.sep)
    total = sum(len(files) + len(dirs) for _, dirs, files in os.walk(folder))
    count = 0
    for root, dirs, files in os.walk(folder):
        cur_depth = root.count(os.sep) - base_depth
        if cur_depth > max_depth:
            dirs[:] = []
            continue
        for f in files:
            result.append((f, os.path.join(root, f)))
            count += 1
            if progress_callback:
                progress_callback(count, total)
        for d in dirs:
            result.append((d, os.path.join(root, d)))
            count += 1
            if progress_callback:
                progress_callback(count, total)
    return result

def build_duplicate_groups(entries, threshold, user_keywords):
    normalized = {e[1]: normalize(e[0]) for e in entries}
    groups = []
    used = set()
    for i, (name1, path1) in enumerate(entries):
        if path1 in used:
            continue
        group = [(name1, path1)]
        norm1 = normalized[path1]
        for name2, path2 in entries[i+1:]:
            if path2 in used:
                continue
            norm2 = normalized[path2]
            if is_version_variant(name1, name2, user_keywords):
                continue
            if SequenceMatcher(None, norm1, norm2).ratio() >= threshold:
                group.append((name2, path2))
                used.add(path2)
        if len(group) > 1:
            used.update([p for _, p in group])
            groups.append(group)
    return groups

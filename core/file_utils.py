import os
import re
import platform
import subprocess
from difflib import SequenceMatcher
from collections import defaultdict
from typing import List, Tuple, Optional, Callable, Dict, Set

def extract_ignore_keywords(raw_input: str) -> List[str]:
    """Extract keywords from brackets in the input string."""
    return re.findall(r'[【\(\[]([^\)\]\u3011]+)[\)\]\u3011]', raw_input)

def normalize(name: str) -> str:
    """Normalize file/folder names for comparison."""
    name = re.sub(r'[\\/]', '', name)
    name = re.sub(r'[\(\[].*?[\)\]]', '', name)
    name = re.sub(r'(DL版|パッケージ版|多国語版|files|canplay|Chinese|English|Espanol)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[第]?[一二三四五六七八九十0-9]+[話章部巻代]', '', name)
    name = re.sub(r'[\d]{6,}', '', name)
    name = re.sub(r'\.[a-zA-Z0-9]+$', '', name)
    name = re.sub(r'[\s\-・_]+', '', name)
    return name.strip().lower()

def is_version_variant(a: str, b: str, user_keywords: List[str]) -> bool:
    """Check if two names are version variants of each other."""
    version_patterns = [
        r'外传\d+', r'外传[一二三四五六七八九十]', r'vol\.?\s*\d+',
        r'episode\s*\d+', r'ep\s*\d+', r'part\s*\d+',
        r'CASE\.?\s*\d+', r'\b\d+\s*th\b', r'\d+\.\d+',
        r'[一二三四五六七八九十]+$'
    ] + [re.escape(k) for k in user_keywords]
    return any(re.search(p, a, re.IGNORECASE) and re.search(p, b, re.IGNORECASE) for p in version_patterns)

def collect_files(folder: str, max_depth: int, progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Tuple[str, str, int]]:
    """Collect files and directories up to max_depth with optional progress callback."""
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
            result.append((f, os.path.join(root, f), cur_depth))
            count += 1
            if progress_callback:
                progress_callback(count, total)
                
        for d in dirs:
            result.append((d, os.path.join(root, d), cur_depth))
            count += 1
            if progress_callback:
                progress_callback(count, total)
                
    return result

def open_file_location(path: str) -> None:
    """Open file location in system file manager."""
    if platform.system() == "Windows":
        if os.path.isdir(path):
            os.startfile(path)
        else:
            subprocess.run(["explorer", "/select,", path])
    elif platform.system() == "Darwin":
        subprocess.run(["open", "-R", path])  # macOS
    else:
        subprocess.run(["xdg-open", os.path.dirname(path)])  # Linux

def _filter_entries_by_depth(entries: List[Tuple[str, str, int]], target_depth: int) -> List[Tuple[str, str, int]]:
    """Filter entries to only include those at the specified depth level."""
    return [entry for entry in entries if entry[2] == target_depth]

def _group_entries_by_folder(entries: List[Tuple[str, str, int]]) -> Dict[str, List[Tuple[str, str]]]:
    """Group entries by their parent folder."""
    groups_by_folder = defaultdict(list)
    for name, path, _ in entries:
        folder = os.path.dirname(path)
        groups_by_folder[folder].append((name, path))
    return groups_by_folder

def _find_duplicates_in_folder(
    group_entries: List[Tuple[str, str]], 
    threshold: float, 
    user_keywords: List[str]
) -> List[List[Tuple[str, str]]]:
    """Find duplicate groups within a single folder."""
    if len(group_entries) < 2:
        return []
    
    # Pre-compute normalized names for efficiency
    normalized_names = {path: normalize(name) for name, path in group_entries}
    used_paths: Set[str] = set()
    folder_groups = []
    
    for i, (name1, path1) in enumerate(group_entries):
        if path1 in used_paths:
            continue
            
        current_group = [(name1, path1)]
        norm1 = normalized_names[path1]
        
        # Compare with remaining entries
        for name2, path2 in group_entries[i + 1:]:
            if path2 in used_paths:
                continue
                
            # Skip version variants
            if is_version_variant(name1, name2, user_keywords):
                continue
                
            norm2 = normalized_names[path2]
            similarity = SequenceMatcher(None, norm1, norm2).ratio()
            
            if similarity >= threshold:
                current_group.append((name2, path2))
                used_paths.add(path2)
        
        # Only add groups with multiple items
        if len(current_group) > 1:
            used_paths.update(path for _, path in current_group)
            folder_groups.append(current_group)
    
    return folder_groups

def build_duplicate_groups(
    entries: List[Tuple[str, str, int]], 
    threshold: float, 
    user_keywords: List[str], 
    target_depth: Optional[int] = None
) -> List[List[Tuple[str, str]]]:
    """
    Build groups of duplicate files/folders based on similarity threshold.
    
    Args:
        entries: List of (name, path, depth) tuples
        threshold: Similarity threshold (0.0 to 1.0)
        user_keywords: Keywords to identify version variants
        target_depth: Optional depth filter - only process entries at this depth
        
    Returns:
        List of duplicate groups, where each group is a list of (name, path) tuples
    """
    # Filter by depth if specified
    if target_depth is not None:
        entries = _filter_entries_by_depth(entries, target_depth)
    
    if not entries:
        return []
    
    # Group entries by folder
    groups_by_folder = _group_entries_by_folder(entries)
    
    # Find duplicates within each folder
    all_groups = []
    for folder_entries in groups_by_folder.values():
        folder_duplicates = _find_duplicates_in_folder(folder_entries, threshold, user_keywords)
        all_groups.extend(folder_duplicates)
    
    return all_groups

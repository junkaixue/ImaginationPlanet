# ✅ Mac-Specific Features Now Merged!

## Update: `irunning.py` is Now Obsolete

The Mac-specific optimizations from `irunning.py` have been **merged into** `running.py`! 🎉

### What Was Merged

All Mac-specific features are now automatically detected in `running.py`:

1. **Scaling factor**: Auto-set to `1` on Mac (was hardcoded in irunning)
2. **Scroll amount**: Auto-uses `100` on Mac, `10` on Windows
3. **Cat grab count**: Auto-set to `10` on Mac, `5` on Windows
4. **Go Home feature**: Now available as parameter: `go_home=True`
5. **Timing adjustments**: Mac uses `sleep(4)` vs Windows `sleep(2)`

### Platform Detection

`running.py` now detects Mac automatically:
```python
is_mac = platform.system() == "Darwin"

# Mac-specific optimizations are applied automatically
if self.is_mac:
    self.cg = 10              # More cat grabs
    self.sft = 1              # Scaling factor
    scroll_up = 100           # Larger scroll
    sleep_time = 4            # Longer waits
```

### Usage on Mac

Just use `running.py` - it automatically optimizes for Mac!

```bash
python imaginationplanet.py -l=True     # Light run
python imaginationplanet.py -r=True     # Regular run  
python imaginationplanet.py -f=True     # Fight only
```

**With go_home feature:**
```python
from running import MainRun

r = MainRun(skip_cat_grab=False, go_home=True)
r.light_run()
```

### File Status

- ✅ **`running.py`** - Unified, cross-platform, Mac-optimized
- ⚠️ **`irunning.py`** - **OBSOLETE** (can be deleted)

---

## Benefits of Merged Version

Before (separate files):
- ❌ Had to maintain `running.py` and `irunning.py`
- ❌ Duplicate code (~250 lines)
- ❌ Manual file switching between platforms

After (merged):
- ✅ Single `running.py` for all platforms
- ✅ Automatic Mac detection and optimization
- ✅ No duplicate code
- ✅ Same API, works everywhere

---

**Bottom Line**: Use `running.py` for everything. Mac optimizations are automatic! You can safely delete `irunning.py`. 🚀

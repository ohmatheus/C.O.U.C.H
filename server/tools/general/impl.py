import subprocess

from state import AppState

STOP_SENTINEL = "__stop_listening__"


def set_volume(level: int, state: AppState, **_: object) -> str:
    subprocess.run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"],
        check=True,
    )
    state.volume = level
    return f"Volume set to {level}%"


def volume_up(state: AppState, **_: object) -> str:
    subprocess.run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
        check=True,
    )
    new_vol = min(100, state.volume + 10)
    state.volume = new_vol
    return f"Volume increased (approximately {new_vol}%)"


def volume_down(state: AppState, **_: object) -> str:
    subprocess.run(
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
        check=True,
    )
    new_vol = max(0, state.volume - 10)
    state.volume = new_vol
    return f"Volume decreased (approximately {new_vol}%)"


def stop_listening(state: AppState, **_: object) -> str:
    state.active_app = None
    return STOP_SENTINEL


def press_key(key: str, **_: object) -> str:
    subprocess.run(["xdotool", "key", key], check=True)
    return f"Key pressed: {key}"


def do_nothing(**_: object) -> str:
    return "__do_nothing__"

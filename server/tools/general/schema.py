from pydantic import Field

from tools.registry import ToolEntry, ToolParams
from tools.general.impl import do_nothing, press_key, set_volume, stop_listening, volume_down, volume_up


class SetVolume(ToolEntry):
    name = "set_volume"
    description = "Set the system volume to a specific level."
    fn = staticmethod(set_volume)

    class Params(ToolParams):
        level: int = Field(description="Volume level between 0 and 100.")


class VolumeUp(ToolEntry):
    name = "volume_up"
    description = "Increase the system volume by 10%."
    fn = staticmethod(volume_up)


class VolumeDown(ToolEntry):
    name = "volume_down"
    description = "Decrease the system volume by 10%."
    fn = staticmethod(volume_down)


class PressKey(ToolEntry):
    name = "press_key"
    description = "Send a keystroke to the active window using xdotool. Useful for controlling non-browser applications."
    fn = staticmethod(press_key)

    class Params(ToolParams):
        key: str = Field(description="xdotool key name, e.g. 'space', 'Escape', 'ctrl+l'.")


class DoNothing(ToolEntry):
    name = "do_nothing"
    description = "Call this when the command does not match any available tool. Has no effect."
    fn = staticmethod(do_nothing)


class StopListening(ToolEntry):
    name = "stop_listening"
    description = "End the listening session and go to sleep. Call ONLY when the user explicitly asks to stop (e.g. 'stop', 'go to sleep', 'stop listening')."
    fn = staticmethod(stop_listening)


ENTRIES: list[type[ToolEntry]] = [SetVolume, VolumeUp, VolumeDown, PressKey, DoNothing, StopListening]

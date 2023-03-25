from dataclasses import asdict

from textual import events
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ..models import BookMetadata, Config, KeyMap, TocEntry
from ..utils.keys_parser import dispatch_key
from .contents import Table
from .events import FollowThis


class Window(Widget):
    can_focus = True

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        keymaps = self.config.keymaps
        self.keymaps = [
            KeyMap(keymaps.close, self.action_close),
            KeyMap(keymaps.scroll_down, self.action_scroll_down),
            KeyMap(keymaps.scroll_up, self.action_scroll_up),
            KeyMap(keymaps.page_down, self.action_page_down),
            KeyMap(keymaps.page_up, self.action_page_up),
        ]

    async def on_key(self, event: events.Key) -> None:
        await dispatch_key(self.keymaps, event)

    def on_mount(self) -> None:
        # NOTE: somehow this method is automatically inherited
        # even if the child class overriding this without super().on_moun()
        self.focus(False)

        # NOTE: set here instead of in CSS file
        # so it will be responsive to screen size
        screen_size = self.screen.size
        self.styles.margin = (screen_size.height // 10, screen_size.width // 10)

    def action_close(self) -> None:
        self.remove()


class Alert(Window):
    border_title = "❗"

    def __init__(self, config: Config, message: str):
        super().__init__(config)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Static(self.message)

    # NOTE: self.render() is low level API
    # so, this won't be any auto scroll-overflow
    # use self.compose() instead
    # def render(self):


class Metadata(Window):
    border_title = "Metadata"

    def __init__(self, config: Config, metadata: BookMetadata):
        super().__init__(config)
        self.metadata = metadata

    def compose(self) -> ComposeResult:
        yield Table(headers=["key", "value"], rows=[(k, v) for k, v in asdict(self.metadata).items()])


class FollowButton(Widget):
    can_focus = True

    def __init__(self, config: Config, label: str, value: str):
        super().__init__()
        self.config = config
        self.value = value
        self.label = label

    async def on_key(self, event: events.Key) -> None:
        await dispatch_key([KeyMap(["enter"], self.action_follow_this)], event, propagate=False)

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        self.focus()

    def action_follow_this(self) -> None:
        self.post_message(FollowThis(self.value))

    def render(self):
        return self.label

    async def on_click(self) -> None:
        # self.post_message(events.DescendantFocus())
        # return await super()._on_click(event)
        self.action_follow_this()


class ToC(Window):
    border_title = "Table of Contents"

    def __init__(self, config: Config, entries: list[TocEntry], initial_focused_id: str | None = None):
        super().__init__(config)
        self.entries = entries
        self.initial_focused_id = initial_focused_id
        self.entry_widgets = [FollowButton(self.config, entry.label, entry.value) for entry in self.entries]
        self.keymaps = [
            KeyMap(config.keymaps.close + config.keymaps.open_toc, self.action_close),
            KeyMap(config.keymaps.scroll_down, self.action_focus_next_child),
            KeyMap(config.keymaps.scroll_up, self.action_focus_prev_child),
            KeyMap(config.keymaps.home, lambda: self.entry_widgets[0].focus()),
            KeyMap(config.keymaps.end, lambda: self.entry_widgets[-1].focus()),
        ]

    def on_focus(self) -> None:
        # always make the focus to the entries
        # and let the entries pass the key event to this window
        if len(self.entries):
            if self.initial_focused_id is None:
                self.entry_widgets[0].focus()
            else:
                for w in self.entry_widgets:
                    if w.value == self.initial_focused_id:
                        w.focus()
                        w.scroll_visible(top=True)
                        break

    # TODO: simplify
    def action_focus_next_child(self) -> None:
        try:
            next(w for w in self.entry_widgets if w.has_focus)
        except StopIteration:
            self.entry_widgets[0].focus()
            return

        for idx, widget in enumerate(self.entry_widgets):
            if self.entry_widgets[idx - 1].has_focus:
                widget.focus()

    # TODO: simplify
    def action_focus_prev_child(self) -> None:
        try:
            next(w for w in self.entry_widgets if w.has_focus)
        except StopIteration:
            self.entry_widgets[-1].focus()
            return

        children = list(reversed(self.entry_widgets))
        for idx, widget in enumerate(children):
            if children[idx - 1].has_focus:
                widget.focus()

    def compose(self) -> ComposeResult:
        yield from self.entry_widgets

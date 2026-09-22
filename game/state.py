"""A snapshot of the whole Herdr session, from one `session.snapshot` call."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def _rect(d):
    d = d or {}
    return Rect(d.get("x", 0), d.get("y", 0), d.get("width", 0), d.get("height", 0))


@dataclass
class Pane:
    id: str
    ws: str
    tab: str
    focused: bool
    label: Optional[str]
    cwd: str
    agent: Optional[str]
    status: str
    scroll: int = 0          # rows scrolled up from the bottom
    history: int = 0         # rows of scrollback available
    rect: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))
    terminal: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def name(self):
        return self.label or ""


@dataclass
class Split:
    id: str
    direction: str   # "right" (side by side) or "down" (stacked)
    ratio: float
    rect: Rect


@dataclass
class Tab:
    id: str
    ws: str
    label: str
    number: int
    focused: bool
    zoomed: bool = False
    area: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))
    focused_pane: Optional[str] = None
    panes: List[Pane] = field(default_factory=list)   # in layout order
    splits: List[Split] = field(default_factory=list)
    status: str = "unknown"

    def pane(self, pid):
        for p in self.panes:
            if p.id == pid:
                return p
        return None

    def by_label(self, label):
        for p in self.panes:
            if p.label == label:
                return p
        return None

    def leftmost(self):
        return min(self.panes, key=lambda p: (p.rect.x, p.rect.y))

    def rightmost(self):
        return max(self.panes, key=lambda p: (p.rect.right, -p.rect.y))

    def corner(self, which):
        """tl / tr / bl / br: the pane in that corner of the tab."""
        ps = self.panes
        minx, maxr = min(p.rect.x for p in ps), max(p.rect.right for p in ps)
        miny, maxb = min(p.rect.y for p in ps), max(p.rect.bottom for p in ps)
        for p in ps:
            horiz = p.rect.x == minx if which[1] == "l" else p.rect.right == maxr
            vert = p.rect.y == miny if which[0] == "t" else p.rect.bottom == maxb
            if horiz and vert:
                return p
        x = minx if which[1] == "l" else maxr
        y = miny if which[0] == "t" else maxb
        return min(ps, key=lambda p: (p.rect.cx - x) ** 2 + (p.rect.cy - y) ** 2)

    def is_grid(self, cols, rows):
        if len(self.panes) != cols * rows:
            return False
        xs = sorted({p.rect.x for p in self.panes})
        ys = sorted({p.rect.y for p in self.panes})
        return len(xs) == cols and len(ys) == rows

    def columns(self):
        return len({p.rect.x for p in self.panes})

    def count(self, direction):
        return sum(1 for s in self.splits if s.direction == direction)

    def order(self):
        """Pane ids in reading order (top-left to bottom-right)."""
        return [p.id for p in sorted(self.panes, key=lambda p: (p.rect.y, p.rect.x))]


@dataclass
class Workspace:
    id: str
    label: str
    number: int
    focused: bool
    active_tab: Optional[str]
    tabs: List[Tab] = field(default_factory=list)
    status: str = "unknown"

    def tab_named(self, label):
        for t in self.tabs:
            if t.label == label:
                return t
        return None

    @property
    def tab(self):
        for t in self.tabs:
            if t.id == self.active_tab:
                return t
        return self.tabs[0] if self.tabs else None


@dataclass
class Agent:
    pane: str
    ws: str
    tab: str
    agent: str
    status: str
    name: Optional[str] = None


class Snapshot:
    def __init__(self, raw, client=None):
        self.raw = raw
        self.client = client or {}     # {"cols", "rows", "attached", "session"} from the launcher
        self.fws = raw.get("focused_workspace_id")
        self.ftab = raw.get("focused_tab_id")
        self.fpane = raw.get("focused_pane_id")
        layouts = {l["tab_id"]: l for l in raw.get("layouts", [])}
        panes = {}
        for p in raw.get("panes", []):
            sc = p.get("scroll") or {}
            panes[p["pane_id"]] = Pane(
                id=p["pane_id"], ws=p.get("workspace_id", ""), tab=p.get("tab_id", ""),
                focused=bool(p.get("focused")), label=p.get("label"), cwd=p.get("cwd", ""),
                agent=p.get("agent"), status=p.get("agent_status", "unknown"),
                scroll=sc.get("offset_from_bottom", 0), history=sc.get("max_offset_from_bottom", 0),
                terminal=p.get("terminal_id", ""), raw=p)
        self.panes: Dict[str, Pane] = panes
        tabs = {}
        for t in raw.get("tabs", []):
            lay = layouts.get(t["tab_id"], {})
            tab = Tab(id=t["tab_id"], ws=t.get("workspace_id", ""), label=t.get("label", ""),
                      number=t.get("number", 0), focused=bool(t.get("focused")),
                      zoomed=bool(lay.get("zoomed")), area=_rect(lay.get("area")),
                      focused_pane=lay.get("focused_pane_id"), status=t.get("agent_status", "unknown"))
            for lp in lay.get("panes", []):
                p = panes.get(lp["pane_id"])
                if p is None:
                    continue
                p.rect = _rect(lp.get("rect"))
                tab.panes.append(p)
            for s in lay.get("splits", []):
                tab.splits.append(Split(s.get("id", ""), s.get("direction", ""), s.get("ratio", 0.5), _rect(s.get("rect"))))
            tabs[tab.id] = tab
        self.tabs: Dict[str, Tab] = tabs
        wss = []
        for w in raw.get("workspaces", []):
            ws = Workspace(id=w["workspace_id"], label=w.get("label", ""), number=w.get("number", 0),
                           focused=bool(w.get("focused")), active_tab=w.get("active_tab_id"),
                           status=w.get("agent_status", "unknown"))
            ws.tabs = sorted([t for t in tabs.values() if t.ws == ws.id], key=lambda t: t.number)
            wss.append(ws)
        self.workspaces: List[Workspace] = sorted(wss, key=lambda w: w.number)
        self.agents = [Agent(a["pane_id"], a.get("workspace_id", ""), a.get("tab_id", ""), a.get("agent", ""),
                             a.get("agent_status", "unknown"), a.get("name"))
                       for a in raw.get("agents", [])]

    # ------------------------------------------------------------ focus

    @property
    def ws(self) -> Optional[Workspace]:
        for w in self.workspaces:
            if w.id == self.fws:
                return w
        return None

    @property
    def tab(self) -> Optional[Tab]:
        return self.tabs.get(self.ftab)

    @property
    def pane(self) -> Optional[Pane]:
        return self.panes.get(self.fpane)

    # ------------------------------------------------------------ lookups

    def workspace_named(self, label):
        for w in self.workspaces:
            if w.label == label:
                return w
        return None

    def pane_labelled(self, label):
        for p in self.panes.values():
            if p.label == label:
                return p
        return None

    def agent_in(self, pane_id):
        for a in self.agents:
            if a.pane == pane_id:
                return a
        return None

    @property
    def attached(self):
        return bool(self.client.get("attached"))

    @property
    def attached_session(self):
        return self.client.get("session") if self.attached else None

    @property
    def cols(self):
        return self.client.get("cols", 0)

    def sidebar_width(self):
        """Columns Herdr gives its sidebar (0 when hidden, ~4 when collapsed)."""
        t = self.tab
        if not t or not self.cols:
            return None
        return self.cols - t.area.w


def take(herdr, client=None):
    raw = herdr.snapshot_raw()
    if raw is None:
        return None
    return Snapshot(raw, client)

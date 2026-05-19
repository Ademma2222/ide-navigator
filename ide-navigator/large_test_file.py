#!/usr/bin/env python3
"""
Large Python test file for IDE plugin testing.
Contains many classes, functions, methods, decorators, and patterns.
"""

from __future__ import annotations

import abc
import asyncio
import collections
import contextlib
import dataclasses
import datetime
import enum
import functools
import hashlib
import inspect
import itertools
import json
import logging
import math
import operator
import os
import pathlib
import queue
import random
import re
import string
import sys
import threading
import time
import typing
import uuid
import warnings
from collections import defaultdict, deque, namedtuple, OrderedDict
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, IntEnum, Flag, auto
from functools import wraps, lru_cache, partial, reduce
from typing import (
    Any, Callable, ClassVar, Dict, FrozenSet, Generator,
    Generic, Iterable, Iterator, List, Literal, Optional,
    Protocol, Sequence, Set, Tuple, Type, TypeVar, Union,
    overload, runtime_checkable,
)

# ─────────────────────────────────────────────
# Type variables
# ─────────────────────────────────────────────

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
N = TypeVar("N", int, float)
kkkk = 312445

logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MAX_RETRIES: int = 5
DEFAULT_TIMEOUT: float = 30.0
VERSION: str = "2.7.1"
PI: float = math.pi
GOLDEN_RATIO: float = (1 + math.sqrt(5)) / 2
PRIMES_SMALL: List[int] = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    CYAN = "cyan"
    MAGENTA = "magenta"
    WHITE = "white"
    BLACK = "black"


class Direction(IntEnum):
    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270


class Permission(Flag):
    NONE = 0
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    ALL = READ | WRITE | EXECUTE


class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# ─────────────────────────────────────────────
# Named tuples & dataclasses
# ─────────────────────────────────────────────

Point2D = namedtuple("Point2D", ["x", "y"])
Point3D = namedtuple("Point3D", ["x", "y", "z"])
RGB = namedtuple("RGB", ["r", "g", "b"])


@dataclass
class Vector2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide vector by zero")
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __abs__(self) -> float:
        return self.magnitude()

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self) -> Vector2:
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return self / mag

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def angle_to(self, other: Vector2) -> float:
        dot = self.dot(other)
        mags = self.magnitude() * other.magnitude()
        if mags == 0:
            return 0.0
        return math.acos(max(-1, min(1, dot / mags)))

    def rotate(self, angle_rad: float) -> Vector2:
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Vector2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a,
        )

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @classmethod
    def from_angle(cls, angle_rad: float, magnitude: float = 1.0) -> Vector2:
        return cls(math.cos(angle_rad) * magnitude, math.sin(angle_rad) * magnitude)

    @classmethod
    def zero(cls) -> Vector2:
        return cls(0.0, 0.0)

    @classmethod
    def one(cls) -> Vector2:
        return cls(1.0, 1.0)


@dataclass
class Rectangle:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

    @property
    def center(self) -> Point2D:
        return Point2D(self.x + self.width / 2, self.y + self.height / 2)

    def contains(self, point: Point2D) -> bool:
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)

    def intersects(self, other: Rectangle) -> bool:
        return not (self.x + self.width < other.x or
                    other.x + other.width < self.x or
                    self.y + self.height < other.y or
                    other.y + other.height < self.y)

    def union(self, other: Rectangle) -> Rectangle:
        x1 = min(self.x, other.x)
        y1 = min(self.y, other.y)
        x2 = max(self.x + self.width, other.x + other.width)
        y2 = max(self.y + self.height, other.y + other.height)
        return Rectangle(x1, y1, x2 - x1, y2 - y1)

    def scale(self, factor: float) -> Rectangle:
        cx, cy = self.center
        nw = self.width * factor
        nh = self.height * factor
        return Rectangle(cx - nw / 2, cy - nh / 2, nw, nh)

    def translate(self, dx: float, dy: float) -> Rectangle:
        return Rectangle(self.x + dx, self.y + dy, self.width, self.height)


@dataclass(frozen=True)
class ImmutableConfig:
    host: str
    port: int
    debug: bool = False
    timeout: float = DEFAULT_TIMEOUT
    max_connections: int = 100
    tags: FrozenSet[str] = field(default_factory=frozenset)

    def with_host(self, host: str) -> ImmutableConfig:
        return dataclasses.replace(self, host=host)

    def with_port(self, port: int) -> ImmutableConfig:
        return dataclasses.replace(self, port=port)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImmutableConfig:
        return cls(**data)

    @classmethod
    def localhost(cls, port: int = 8080) -> ImmutableConfig:
        return cls(host="localhost", port=port)


# ─────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────

def retry(max_attempts: int = 3, delay: float = 1.0, exceptions=(Exception,)):
    """Retry decorator with configurable attempts and delay."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
            raise last_exc
        return wrapper
    return decorator


def timer(func: Callable) -> Callable:
    """Measure and log execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper


def deprecated(reason: str = ""):
    """Mark a function as deprecated."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated. {reason}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def singleton(cls: Type[T]) -> Type[T]:
    """Singleton class decorator."""
    instances: Dict[Type, Any] = {}

    @wraps(cls)
    def get_instance(*args, **kwargs) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance  # type: ignore


def validate_types(**type_map):
    """Runtime type validation decorator."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            for param_name, expected_type in type_map.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not isinstance(value, expected_type):
                        raise TypeError(
                            f"Parameter '{param_name}' expected {expected_type.__name__}, "
                            f"got {type(value).__name__}"
                        )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def memoize(func: Callable) -> Callable:
    """Simple memoization without size limit."""
    cache: Dict[Any, Any] = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache  # type: ignore
    wrapper.cache_clear = lambda: cache.clear()  # type: ignore
    return wrapper


def log_calls(level: str = "DEBUG"):
    """Log function calls with arguments."""
    log_fn = getattr(logger, level.lower(), logger.debug)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            log_fn(f"Calling {func.__name__}({args!r}, {kwargs!r})")
            result = func(*args, **kwargs)
            log_fn(f"{func.__name__} returned {result!r}")
            return result
        return wrapper
    return decorator


# ─────────────────────────────────────────────
# Context managers
# ─────────────────────────────────────────────

@contextmanager
def timer_context(label: str = "block") -> Generator[None, None, None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"[{label}] elapsed: {elapsed:.4f}s")


@contextmanager
def suppress_exceptions(*exc_types) -> Generator[None, None, None]:
    try:
        yield
    except exc_types:
        pass


@contextmanager
def temp_directory() -> Generator[pathlib.Path, None, None]:
    import tempfile, shutil
    tmpdir = pathlib.Path(tempfile.mkdtemp())
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@asynccontextmanager
async def async_timer(label: str = "async block") -> typing.AsyncGenerator[None, None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"[{label}] async elapsed: {elapsed:.4f}s")


# ─────────────────────────────────────────────
# Abstract base classes
# ─────────────────────────────────────────────

class Shape(abc.ABC):
    """Abstract base for geometric shapes."""

    @abc.abstractmethod
    def area(self) -> float: ...

    @abc.abstractmethod
    def perimeter(self) -> float: ...

    @abc.abstractmethod
    def contains(self, point: Point2D) -> bool: ...

    def scale(self, factor: float) -> Shape:
        raise NotImplementedError

    def describe(self) -> str:
        return (f"{self.__class__.__name__}: "
                f"area={self.area():.2f}, perimeter={self.perimeter():.2f}")


class Circle(Shape):
    def __init__(self, cx: float, cy: float, radius: float) -> None:
        if radius <= 0:
            raise ValueError("Radius must be positive")
        self.cx = cx
        self.cy = cy
        self.radius = radius

    def area(self) -> float:
        return PI * self.radius ** 2

    def perimeter(self) -> float:
        return 2 * PI * self.radius

    def contains(self, point: Point2D) -> bool:
        return (point.x - self.cx) ** 2 + (point.y - self.cy) ** 2 <= self.radius ** 2

    def scale(self, factor: float) -> Circle:
        return Circle(self.cx, self.cy, self.radius * factor)

    def intersects(self, other: Circle) -> bool:
        dist = math.sqrt((self.cx - other.cx) ** 2 + (self.cy - other.cy) ** 2)
        return dist < self.radius + other.radius

    def bounding_box(self) -> Rectangle:
        return Rectangle(
            self.cx - self.radius,
            self.cy - self.radius,
            2 * self.radius,
            2 * self.radius,
        )


class Triangle(Shape):
    def __init__(self, a: Point2D, b: Point2D, c: Point2D) -> None:
        self.a = a
        self.b = b
        self.c = c

    def _side_lengths(self) -> Tuple[float, float, float]:
        ab = math.dist(self.a, self.b)
        bc = math.dist(self.b, self.c)
        ca = math.dist(self.c, self.a)
        return ab, bc, ca

    def area(self) -> float:
        ab, bc, ca = self._side_lengths()
        s = (ab + bc + ca) / 2
        return math.sqrt(max(0, s * (s - ab) * (s - bc) * (s - ca)))

    def perimeter(self) -> float:
        return sum(self._side_lengths())

    def contains(self, point: Point2D) -> bool:
        def sign(p1, p2, p3):
            return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)
        d1 = sign(point, self.a, self.b)
        d2 = sign(point, self.b, self.c)
        d3 = sign(point, self.c, self.a)
        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)

    def is_equilateral(self) -> bool:
        ab, bc, ca = self._side_lengths()
        return math.isclose(ab, bc) and math.isclose(bc, ca)

    def is_right(self) -> bool:
        sides = sorted(self._side_lengths())
        return math.isclose(sides[0] ** 2 + sides[1] ** 2, sides[2] ** 2)

    def centroid(self) -> Point2D:
        return Point2D(
            (self.a.x + self.b.x + self.c.x) / 3,
            (self.a.y + self.b.y + self.c.y) / 3,
        )


# ─────────────────────────────────────────────
# Generic data structures
# ─────────────────────────────────────────────

class Stack(Generic[T]):
    """Thread-safe generic stack."""

    def __init__(self) -> None:
        self._data: List[T] = []
        self._lock = threading.Lock()

    def push(self, item: T) -> None:
        with self._lock:
            self._data.append(item)

    def pop(self) -> T:
        with self._lock:
            if not self._data:
                raise IndexError("pop from empty stack")
            return self._data.pop()

    def peek(self) -> T:
        with self._lock:
            if not self._data:
                raise IndexError("peek from empty stack")
            return self._data[-1]

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._data) == 0

    def size(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return self.size()

    def __repr__(self) -> str:
        return f"Stack({self._data!r})"


class Queue(Generic[T]):
    """Thread-safe generic FIFO queue."""

    def __init__(self, maxsize: int = 0) -> None:
        self._q: queue.Queue[T] = queue.Queue(maxsize=maxsize)

    def enqueue(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        self._q.put(item, block=block, timeout=timeout)

    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> T:
        return self._q.get(block=block, timeout=timeout)

    def peek(self) -> Optional[T]:
        with self._q.mutex:
            if self._q.queue:
                return self._q.queue[0]
            return None

    def is_empty(self) -> bool:
        return self._q.empty()

    def size(self) -> int:
        return self._q.qsize()

    def task_done(self) -> None:
        self._q.task_done()

    def join(self) -> None:
        self._q.join()


class LinkedListNode(Generic[T]):
    def __init__(self, value: T, next_node: Optional[LinkedListNode[T]] = None) -> None:
        self.value = value
        self.next = next_node


class LinkedList(Generic[T]):
    """Singly linked list."""

    def __init__(self) -> None:
        self.head: Optional[LinkedListNode[T]] = None
        self._size = 0

    def prepend(self, value: T) -> None:
        self.head = LinkedListNode(value, self.head)
        self._size += 1

    def append(self, value: T) -> None:
        node = LinkedListNode(value)
        if self.head is None:
            self.head = node
        else:
            curr = self.head
            while curr.next:
                curr = curr.next
            curr.next = node
        self._size += 1

    def remove(self, value: T) -> bool:
        if self.head is None:
            return False
        if self.head.value == value:
            self.head = self.head.next
            self._size -= 1
            return True
        curr = self.head
        while curr.next:
            if curr.next.value == value:
                curr.next = curr.next.next
                self._size -= 1
                return True
            curr = curr.next
        return False

    def contains(self, value: T) -> bool:
        curr = self.head
        while curr:
            if curr.value == value:
                return True
            curr = curr.next
        return False

    def to_list(self) -> List[T]:
        result = []
        curr = self.head
        while curr:
            result.append(curr.value)
            curr = curr.next
        return result

    def reverse(self) -> None:
        prev = None
        curr = self.head
        while curr:
            nxt = curr.next
            curr.next = prev
            prev = curr
            curr = nxt
        self.head = prev

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        curr = self.head
        while curr:
            yield curr.value
            curr = curr.next


class BinaryTreeNode(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value
        self.left: Optional[BinaryTreeNode[T]] = None
        self.right: Optional[BinaryTreeNode[T]] = None


class BinarySearchTree(Generic[T]):
    """Binary search tree with basic operations."""

    def __init__(self) -> None:
        self.root: Optional[BinaryTreeNode[T]] = None

    def insert(self, value: T) -> None:
        if self.root is None:
            self.root = BinaryTreeNode(value)
        else:
            self._insert(self.root, value)

    def _insert(self, node: BinaryTreeNode[T], value: T) -> None:
        if value < node.value:  # type: ignore
            if node.left is None:
                node.left = BinaryTreeNode(value)
            else:
                self._insert(node.left, value)
        else:
            if node.right is None:
                node.right = BinaryTreeNode(value)
            else:
                self._insert(node.right, value)

    def contains(self, value: T) -> bool:
        return self._contains(self.root, value)

    def _contains(self, node: Optional[BinaryTreeNode[T]], value: T) -> bool:
        if node is None:
            return False
        if value == node.value:
            return True
        if value < node.value:  # type: ignore
            return self._contains(node.left, value)
        return self._contains(node.right, value)

    def inorder(self) -> List[T]:
        result: List[T] = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node: Optional[BinaryTreeNode[T]], result: List[T]) -> None:
        if node:
            self._inorder(node.left, result)
            result.append(node.value)
            self._inorder(node.right, result)

    def preorder(self) -> List[T]:
        result: List[T] = []
        self._preorder(self.root, result)
        return result

    def _preorder(self, node: Optional[BinaryTreeNode[T]], result: List[T]) -> None:
        if node:
            result.append(node.value)
            self._preorder(node.left, result)
            self._preorder(node.right, result)

    def postorder(self) -> List[T]:
        result: List[T] = []
        self._postorder(self.root, result)
        return result

    def _postorder(self, node: Optional[BinaryTreeNode[T]], result: List[T]) -> None:
        if node:
            self._postorder(node.left, result)
            self._postorder(node.right, result)
            result.append(node.value)

    def height(self) -> int:
        return self._height(self.root)

    def _height(self, node: Optional[BinaryTreeNode[T]]) -> int:
        if node is None:
            return 0
        return 1 + max(self._height(node.left), self._height(node.right))

    def min_value(self) -> Optional[T]:
        if self.root is None:
            return None
        curr = self.root
        while curr.left:
            curr = curr.left
        return curr.value

    def max_value(self) -> Optional[T]:
        if self.root is None:
            return None
        curr = self.root
        while curr.right:
            curr = curr.right
        return curr.value


class MinHeap(Generic[T]):
    """Min-heap implementation."""

    def __init__(self) -> None:
        self._data: List[T] = []

    def push(self, item: T) -> None:
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop(self) -> T:
        if not self._data:
            raise IndexError("pop from empty heap")
        self._swap(0, len(self._data) - 1)
        item = self._data.pop()
        if self._data:
            self._sift_down(0)
        return item

    def peek(self) -> T:
        if not self._data:
            raise IndexError("peek from empty heap")
        return self._data[0]

    def _sift_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) // 2
            if self._data[idx] < self._data[parent]:  # type: ignore
                self._swap(idx, parent)
                idx = parent
            else:
                break

    def _sift_down(self, idx: int) -> None:
        size = len(self._data)
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            smallest = idx
            if left < size and self._data[left] < self._data[smallest]:  # type: ignore
                smallest = left
            if right < size and self._data[right] < self._data[smallest]:  # type: ignore
                smallest = right
            if smallest != idx:
                self._swap(idx, smallest)
                idx = smallest
            else:
                break

    def _swap(self, i: int, j: int) -> None:
        self._data[i], self._data[j] = self._data[j], self._data[i]

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)


class LRUCache(Generic[K, V]):
    """Least-Recently-Used cache."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self._cache: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> Optional[V]:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: K, value: V) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def remove(self, key: K) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: K) -> bool:
        return key in self._cache

    def keys(self):
        return self._cache.keys()

    def values(self):
        return self._cache.values()

    def items(self):
        return self._cache.items()


# ─────────────────────────────────────────────
# Design patterns
# ─────────────────────────────────────────────

class Observer(Protocol):
    def update(self, event: str, data: Any) -> None: ...


class EventEmitter:
    """Simple publish-subscribe event emitter."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def on(self, event: str, callback: Callable) -> None:
        self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable) -> None:
        self._listeners[event] = [
            cb for cb in self._listeners[event] if cb != callback
        ]

    def emit(self, event: str, *args, **kwargs) -> None:
        for cb in list(self._listeners.get(event, [])):
            cb(*args, **kwargs)

    def once(self, event: str, callback: Callable) -> None:
        def wrapper(*args, **kwargs):
            callback(*args, **kwargs)
            self.off(event, wrapper)
        self.on(event, wrapper)

    def listener_count(self, event: str) -> int:
        return len(self._listeners.get(event, []))

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        if event:
            self._listeners.pop(event, None)
        else:
            self._listeners.clear()


class Command(abc.ABC):
    """Command pattern base."""

    @abc.abstractmethod
    def execute(self) -> Any: ...

    def undo(self) -> Any:
        raise NotImplementedError("This command does not support undo")


class CommandHistory:
    def __init__(self) -> None:
        self._history: List[Command] = []
        self._redo_stack: List[Command] = []

    def execute(self, command: Command) -> Any:
        result = command.execute()
        self._history.append(command)
        self._redo_stack.clear()
        return result

    def undo(self) -> Any:
        if not self._history:
            raise IndexError("No commands to undo")
        cmd = self._history.pop()
        result = cmd.undo()
        self._redo_stack.append(cmd)
        return result

    def redo(self) -> Any:
        if not self._redo_stack:
            raise IndexError("No commands to redo")
        cmd = self._redo_stack.pop()
        result = cmd.execute()
        self._history.append(cmd)
        return result

    def history_size(self) -> int:
        return len(self._history)


class Builder(Generic[T]):
    """Generic builder pattern helper."""

    def __init__(self, cls: Type[T], **kwargs) -> None:
        self._cls = cls
        self._kwargs: Dict[str, Any] = kwargs

    def set(self, **kwargs) -> Builder[T]:
        self._kwargs.update(kwargs)
        return self

    def build(self) -> T:
        return self._cls(**self._kwargs)


class State(abc.ABC):
    """State machine state."""

    @abc.abstractmethod
    def handle(self, context: StateMachine) -> None: ...

    def on_enter(self, context: StateMachine) -> None:
        pass

    def on_exit(self, context: StateMachine) -> None:
        pass


class StateMachine:
    def __init__(self, initial_state: State) -> None:
        self._state = initial_state
        self._state.on_enter(self)

    def transition(self, new_state: State) -> None:
        self._state.on_exit(self)
        self._state = new_state
        self._state.on_enter(self)

    def handle(self) -> None:
        self._state.handle(self)

    @property
    def current_state(self) -> State:
        return self._state


# ─────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────

def clamp(value: N, min_val: N, max_val: N) -> N:
    return max(min_val, min(max_val, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t, 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def remap(value: float, from_min: float, from_max: float,
          to_min: float, to_max: float) -> float:
    ratio = (value - from_min) / (from_max - from_min)
    return to_min + ratio * (to_max - to_min)


def chunks(iterable: Iterable[T], size: int) -> Iterator[List[T]]:
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, size))
        if not chunk:
            break
        yield chunk


def flatten(nested: Iterable) -> List:
    result = []
    for item in nested:
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def unique(iterable: Iterable[T], key: Optional[Callable[[T], Any]] = None) -> List[T]:
    seen: Set = set()
    result = []
    for item in iterable:
        k = key(item) if key else item
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def group_by(iterable: Iterable[T], key: Callable[[T], K]) -> Dict[K, List[T]]:
    groups: Dict[K, List[T]] = defaultdict(list)
    for item in iterable:
        groups[key(item)].append(item)
    return dict(groups)


def partition(iterable: Iterable[T], predicate: Callable[[T], bool]) -> Tuple[List[T], List[T]]:
    true_items, false_items = [], []
    for item in iterable:
        (true_items if predicate(item) else false_items).append(item)
    return true_items, false_items


def sliding_window(seq: Sequence[T], size: int) -> Iterator[Tuple[T, ...]]:
    for i in range(len(seq) - size + 1):
        yield tuple(seq[i:i + size])


def pairwise(iterable: Iterable[T]) -> Iterator[Tuple[T, T]]:
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def safe_get(d: dict, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
    return d


def truncate(text: str, max_len: int, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def snake_to_pascal(name: str) -> str:
    return "".join(p.title() for p in name.split("_"))


def is_palindrome(s: str) -> bool:
    s = re.sub(r"[^a-zA-Z0-9]", "", s).lower()
    return s == s[::-1]


def count_words(text: str) -> Dict[str, int]:
    words = re.findall(r"\b\w+\b", text.lower())
    return dict(collections.Counter(words))


def generate_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def humanize_bytes(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0  # type: ignore
    return f"{num:.1f} EB"


def humanize_duration(seconds: float) -> str:
    units = [
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    ]
    parts = []
    remaining = int(seconds)
    for name, size in units:
        count = remaining // size
        remaining %= size
        if count:
            parts.append(f"{count} {name}{'s' if count != 1 else ''}")
    return ", ".join(parts) if parts else "0 seconds"


# ─────────────────────────────────────────────
# Math utilities
# ─────────────────────────────────────────────

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def sieve_of_eratosthenes(limit: int) -> List[int]:
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(math.sqrt(limit)) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    return [i for i, v in enumerate(sieve) if v]


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b)


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0:
        return 1
    return reduce(operator.mul, range(1, n + 1), 1)


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("Fibonacci not defined for negative indices")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def fibonacci_sequence(count: int) -> List[int]:
    if count <= 0:
        return []
    if count == 1:
        return [0]
    seq = [0, 1]
    while len(seq) < count:
        seq.append(seq[-1] + seq[-2])
    return seq


def combinations(n: int, r: int) -> int:
    if r > n:
        return 0
    r = min(r, n - r)
    result = 1
    for i in range(r):
        result = result * (n - i) // (i + 1)
    return result


def permutations_count(n: int, r: int) -> int:
    if r > n:
        return 0
    result = 1
    for i in range(n, n - r, -1):
        result *= i
    return result


def mean(data: Sequence[float]) -> float:
    if not data:
        raise ValueError("Cannot compute mean of empty sequence")
    return sum(data) / len(data)


def median(data: Sequence[float]) -> float:
    if not data:
        raise ValueError("Cannot compute median of empty sequence")
    sorted_data = sorted(data)
    n = len(sorted_data)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_data[mid - 1] + sorted_data[mid]) / 2
    return sorted_data[mid]


def variance(data: Sequence[float], ddof: int = 0) -> float:
    if len(data) <= ddof:
        raise ValueError("Not enough data")
    m = mean(data)
    return sum((x - m) ** 2 for x in data) / (len(data) - ddof)


def std_dev(data: Sequence[float], ddof: int = 0) -> float:
    return math.sqrt(variance(data, ddof))


def normalize(data: List[float]) -> List[float]:
    mn, mx = min(data), max(data)
    rng = mx - mn
    if rng == 0:
        return [0.0] * len(data)
    return [(x - mn) / rng for x in data]


def dot_product(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vectors must have the same length")
    return sum(x * y for x, y in zip(a, b))


def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])
    if cols_a != rows_b:
        raise ValueError("Incompatible matrix dimensions")
    result = [[0.0] * cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    return result


def matrix_transpose(m: List[List[float]]) -> List[List[float]]:
    return [list(row) for row in zip(*m)]


# ─────────────────────────────────────────────
# Sorting algorithms
# ─────────────────────────────────────────────

def bubble_sort(data: List[T]) -> List[T]:
    arr = list(data)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:  # type: ignore
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def selection_sort(data: List[T]) -> List[T]:
    arr = list(data)
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:  # type: ignore
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr


def insertion_sort(data: List[T]) -> List[T]:
    arr = list(data)
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:  # type: ignore
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr


def merge_sort(data: List[T]) -> List[T]:
    if len(data) <= 1:
        return list(data)
    mid = len(data) // 2
    left = merge_sort(data[:mid])
    right = merge_sort(data[mid:])
    return _merge(left, right)


def _merge(left: List[T], right: List[T]) -> List[T]:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:  # type: ignore
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def quick_sort(data: List[T]) -> List[T]:
    arr = list(data)
    _quick_sort(arr, 0, len(arr) - 1)
    return arr


def _quick_sort(arr: List[T], low: int, high: int) -> None:
    if low < high:
        pi = _partition(arr, low, high)
        _quick_sort(arr, low, pi - 1)
        _quick_sort(arr, pi + 1, high)


def _partition(arr: List[T], low: int, high: int) -> int:
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:  # type: ignore
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


def heap_sort(data: List[T]) -> List[T]:
    arr = list(data)
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        _heapify(arr, n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        _heapify(arr, i, 0)
    return arr


def _heapify(arr: List[T], n: int, i: int) -> None:
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    if left < n and arr[left] > arr[largest]:  # type: ignore
        largest = left
    if right < n and arr[right] > arr[largest]:  # type: ignore
        largest = right
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        _heapify(arr, n, largest)


# ─────────────────────────────────────────────
# Search algorithms
# ─────────────────────────────────────────────

def binary_search(arr: Sequence[T], target: T) -> int:
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:  # type: ignore
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def linear_search(arr: Sequence[T], target: T) -> int:
    for i, item in enumerate(arr):
        if item == target:
            return i
    return -1


def interpolation_search(arr: Sequence[int], target: int) -> int:
    lo, hi = 0, len(arr) - 1
    while lo <= hi and arr[lo] <= target <= arr[hi]:
        if arr[lo] == arr[hi]:
            return lo if arr[lo] == target else -1
        pos = lo + ((target - arr[lo]) * (hi - lo) // (arr[hi] - arr[lo]))
        if arr[pos] == target:
            return pos
        elif arr[pos] < target:
            lo = pos + 1
        else:
            hi = pos - 1
    return -1


def bfs(graph: Dict[T, List[T]], start: T) -> List[T]:
    visited: Set[T] = set()
    result: List[T] = []
    q: deque[T] = deque([start])
    visited.add(start)
    while q:
        node = q.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                q.append(neighbor)
    return result


def dfs(graph: Dict[T, List[T]], start: T) -> List[T]:
    visited: Set[T] = set()
    result: List[T] = []

    def _dfs(node: T) -> None:
        visited.add(node)
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                _dfs(neighbor)

    _dfs(start)
    return result


def dijkstra(graph: Dict[str, Dict[str, float]], start: str) -> Dict[str, float]:
    import heapq
    distances: Dict[str, float] = {node: float("inf") for node in graph}
    distances[start] = 0.0
    heap = [(0.0, start)]
    while heap:
        dist, node = heapq.heappop(heap)
        if dist > distances[node]:
            continue
        for neighbor, weight in graph.get(node, {}).items():
            new_dist = dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                heapq.heappush(heap, (new_dist, neighbor))
    return distances


# ─────────────────────────────────────────────
# String utilities
# ─────────────────────────────────────────────

def levenshtein_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[n]


def longest_common_subsequence(s1: str, s2: str) -> str:
    m, n = len(s1), len(s2)
    dp = [[""] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + s1[i - 1]
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1], key=len)
    return dp[m][n]


def count_substrings(text: str, pattern: str) -> int:
    count = 0
    start = 0
    while True:
        idx = text.find(pattern, start)
        if idx == -1:
            break
        count += 1
        start = idx + 1
    return count


def word_wrap(text: str, width: int) -> str:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return "\n".join(lines)


def remove_diacritics(text: str) -> str:
    import unicodedata
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def mask_string(s: str, show_last: int = 4, mask_char: str = "*") -> str:
    if len(s) <= show_last:
        return s
    return mask_char * (len(s) - show_last) + s[-show_last:]


# ─────────────────────────────────────────────
# Cryptography helpers
# ─────────────────────────────────────────────

def md5(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def sha512(data: str) -> str:
    return hashlib.sha512(data.encode()).hexdigest()


def generate_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def generate_uuid() -> str:
    return str(uuid.uuid4())


def hmac_sha256(key: str, message: str) -> str:
    import hmac
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


# ─────────────────────────────────────────────
# Async utilities
# ─────────────────────────────────────────────

async def async_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def gather_with_timeout(
    *coros, timeout: float = DEFAULT_TIMEOUT
) -> List[Any]:
    return await asyncio.wait_for(asyncio.gather(*coros), timeout=timeout)


async def retry_async(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    *args,
    **kwargs,
) -> Any:
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay * (2 ** attempt))
    raise last_exc


async def run_in_executor(func: Callable, *args) -> Any:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


async def periodic(func: Callable, interval: float) -> None:
    while True:
        await func()
        await asyncio.sleep(interval)


async def debounce_async(func: Callable, wait: float) -> Callable:
    task: Optional[asyncio.Task] = None

    async def wrapper(*args, **kwargs):
        nonlocal task
        if task:
            task.cancel()
        await asyncio.sleep(wait)
        return await func(*args, **kwargs)

    return wrapper


# ─────────────────────────────────────────────
# Protocols
# ─────────────────────────────────────────────

@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> Dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Serializable: ...


@runtime_checkable
class Comparable(Protocol):
    def __lt__(self, other: Any) -> bool: ...
    def __le__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...
    def __ge__(self, other: Any) -> bool: ...


@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...


# ─────────────────────────────────────────────
# Repository pattern
# ─────────────────────────────────────────────

class Entity:
    def __init__(self, entity_id: Optional[str] = None) -> None:
        self.id: str = entity_id or generate_uuid()
        self.created_at: datetime.datetime = datetime.datetime.utcnow()
        self.updated_at: datetime.datetime = self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Repository(Generic[T], abc.ABC):
    @abc.abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]: ...

    @abc.abstractmethod
    def find_all(self) -> List[T]: ...

    @abc.abstractmethod
    def save(self, entity: T) -> T: ...

    @abc.abstractmethod
    def delete(self, entity_id: str) -> bool: ...

    @abc.abstractmethod
    def count(self) -> int: ...


class InMemoryRepository(Repository[T]):
    def __init__(self) -> None:
        self._store: Dict[str, T] = {}

    def find_by_id(self, entity_id: str) -> Optional[T]:
        return self._store.get(entity_id)

    def find_all(self) -> List[T]:
        return list(self._store.values())

    def save(self, entity: T) -> T:
        entity_id = getattr(entity, "id", str(id(entity)))
        self._store[entity_id] = entity
        return entity

    def delete(self, entity_id: str) -> bool:
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False

    def count(self) -> int:
        return len(self._store)

    def find_where(self, predicate: Callable[[T], bool]) -> List[T]:
        return [e for e in self._store.values() if predicate(e)]

    def clear(self) -> None:
        self._store.clear()


# ─────────────────────────────────────────────
# Pipeline / functional utilities
# ─────────────────────────────────────────────

class Pipeline(Generic[T]):
    def __init__(self, value: T) -> None:
        self._value = value

    def pipe(self, func: Callable[[T], T]) -> Pipeline[T]:
        return Pipeline(func(self._value))

    def map(self, func: Callable[[T], V]) -> Pipeline[V]:  # type: ignore
        return Pipeline(func(self._value))

    def filter(self, predicate: Callable[[T], bool]) -> Optional[Pipeline[T]]:
        return Pipeline(self._value) if predicate(self._value) else None

    def tap(self, func: Callable[[T], None]) -> Pipeline[T]:
        func(self._value)
        return self

    def value(self) -> T:
        return self._value

    def __repr__(self) -> str:
        return f"Pipeline({self._value!r})"


def compose(*funcs: Callable) -> Callable:
    """Right-to-left function composition."""
    return reduce(lambda f, g: lambda *args, **kwargs: f(g(*args, **kwargs)), funcs)


def pipe(*funcs: Callable) -> Callable:
    """Left-to-right function composition."""
    return reduce(lambda f, g: lambda *args, **kwargs: g(f(*args, **kwargs)), funcs)


def curry(func: Callable) -> Callable:
    """Curry a function."""
    sig = inspect.signature(func)
    n_args = len(sig.parameters)

    def curried(*args):
        if len(args) >= n_args:
            return func(*args[:n_args])
        return lambda *more: curried(*(args + more))

    return curried


# ─────────────────────────────────────────────
# Configuration management
# ─────────────────────────────────────────────

class ConfigurationError(Exception):
    """Raised when configuration is invalid."""


class Configuration:
    """Hierarchical configuration with environment overrides."""

    def __init__(self, defaults: Optional[Dict[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = defaults or {}
        self._env_prefix: str = ""

    def set_env_prefix(self, prefix: str) -> None:
        self._env_prefix = prefix.upper()

    def get(self, key: str, default: Any = None) -> Any:
        env_key = f"{self._env_prefix}_{key.upper()}" if self._env_prefix else key.upper()
        if env_key in os.environ:
            return os.environ[env_key]
        return safe_get(self._data, *key.split("."), default=default)

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def require(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise ConfigurationError(f"Required configuration key missing: {key}")
        return value

    def load_dict(self, data: Dict[str, Any]) -> None:
        self._data = deep_merge(self._data, data)

    def load_json(self, json_str: str) -> None:
        self.load_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __repr__(self) -> str:
        return f"Configuration({self._data!r})"


# ─────────────────────────────────────────────
# Rate limiter
# ─────────────────────────────────────────────

class RateLimiter:
    """Token-bucket rate limiter."""

    def __init__(self, rate: float, capacity: float) -> None:
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def acquire(self, tokens: float = 1.0) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait(self, tokens: float = 1.0) -> None:
        while not self.acquire(tokens):
            time.sleep(0.01)

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


# ─────────────────────────────────────────────
# Circuit breaker
# ─────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (time.monotonic() - (self._last_failure_time or 0)) > self.timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._successes = 0
                else:
                    raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                self._on_success()
            return result
        except Exception as e:
            with self._lock:
                self._on_failure()
            raise

    def _on_success(self) -> None:
        self._failures = 0
        if self._state == CircuitState.HALF_OPEN:
            self._successes += 1
            if self._successes >= self.success_threshold:
                self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN


# ─────────────────────────────────────────────
# Object pool
# ─────────────────────────────────────────────

class ObjectPool(Generic[T]):
    def __init__(self, factory: Callable[[], T], max_size: int = 10) -> None:
        self._factory = factory
        self._max_size = max_size
        self._pool: List[T] = []
        self._lock = threading.Lock()

    def acquire(self) -> T:
        with self._lock:
            if self._pool:
                return self._pool.pop()
        return self._factory()

    def release(self, obj: T) -> None:
        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(obj)

    @contextmanager
    def use(self) -> Generator[T, None, None]:
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)

    def pool_size(self) -> int:
        with self._lock:
            return len(self._pool)


# ─────────────────────────────────────────────
# Signal / slot (Qt-inspired)
# ─────────────────────────────────────────────

class Signal(Generic[T]):
    def __init__(self) -> None:
        self._slots: List[Callable[[T], None]] = []

    def connect(self, slot: Callable[[T], None]) -> None:
        if slot not in self._slots:
            self._slots.append(slot)

    def disconnect(self, slot: Callable[[T], None]) -> None:
        self._slots = [s for s in self._slots if s != slot]

    def emit(self, value: T) -> None:
        for slot in list(self._slots):
            slot(value)

    def disconnect_all(self) -> None:
        self._slots.clear()

    def slot_count(self) -> int:
        return len(self._slots)


# ─────────────────────────────────────────────
# Simple expression evaluator
# ─────────────────────────────────────────────

class TokenType(Enum):
    NUMBER = "NUMBER"
    PLUS = "PLUS"
    MINUS = "MINUS"
    MUL = "MUL"
    DIV = "DIV"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: Any


class Lexer:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def error(self) -> None:
        raise ValueError(f"Invalid character at position {self.pos}")

    def advance(self) -> None:
        self.pos += 1

    def skip_whitespace(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.advance()

    def number(self) -> Token:
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == "."):
            self.advance()
        return Token(TokenType.NUMBER, float(self.text[start:self.pos]))

    def next_token(self) -> Token:
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isspace():
                self.skip_whitespace()
                continue
            if ch.isdigit() or ch == ".":
                return self.number()
            self.advance()
            mapping = {
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.MUL,
                "/": TokenType.DIV,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
            }
            if ch in mapping:
                return Token(mapping[ch], ch)
            self.error()
        return Token(TokenType.EOF, None)


class Parser:
    def __init__(self, lexer: Lexer) -> None:
        self.lexer = lexer
        self.current = self.lexer.next_token()

    def eat(self, token_type: TokenType) -> None:
        if self.current.type == token_type:
            self.current = self.lexer.next_token()
        else:
            raise ValueError(f"Expected {token_type}, got {self.current.type}")

    def factor(self) -> float:
        tok = self.current
        if tok.type == TokenType.NUMBER:
            self.eat(TokenType.NUMBER)
            return tok.value
        if tok.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            result = self.expr()
            self.eat(TokenType.RPAREN)
            return result
        if tok.type == TokenType.MINUS:
            self.eat(TokenType.MINUS)
            return -self.factor()
        raise ValueError(f"Unexpected token: {tok}")

    def term(self) -> float:
        result = self.factor()
        while self.current.type in (TokenType.MUL, TokenType.DIV):
            if self.current.type == TokenType.MUL:
                self.eat(TokenType.MUL)
                result *= self.factor()
            else:
                self.eat(TokenType.DIV)
                divisor = self.factor()
                if divisor == 0:
                    raise ZeroDivisionError("Division by zero")
                result /= divisor
        return result

    def expr(self) -> float:
        result = self.term()
        while self.current.type in (TokenType.PLUS, TokenType.MINUS):
            if self.current.type == TokenType.PLUS:
                self.eat(TokenType.PLUS)
                result += self.term()
            else:
                self.eat(TokenType.MINUS)
                result -= self.term()
        return result


def evaluate_expression(expr: str) -> float:
    lexer = Lexer(expr)
    parser = Parser(lexer)
    return parser.expr()


# ─────────────────────────────────────────────
# Simple task scheduler
# ─────────────────────────────────────────────

@dataclass(order=True)
class ScheduledTask:
    run_at: float
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    repeat_interval: Optional[float] = field(default=None, compare=False)


class TaskScheduler:
    def __init__(self) -> None:
        import heapq
        self._tasks: List[ScheduledTask] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._heapq = heapq

    def schedule(
        self,
        func: Callable,
        delay: float,
        *args,
        repeat: Optional[float] = None,
        **kwargs,
    ) -> str:
        task_id = generate_uuid()
        task = ScheduledTask(
            run_at=time.monotonic() + delay,
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            repeat_interval=repeat,
        )
        with self._lock:
            self._heapq.heappush(self._tasks, task)
        return task_id

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            before = len(self._tasks)
            self._tasks = [t for t in self._tasks if t.task_id != task_id]
            self._heapq.heapify(self._tasks)
            return len(self._tasks) < before

    def _run(self) -> None:
        while self._running:
            now = time.monotonic()
            with self._lock:
                due = []
                while self._tasks and self._tasks[0].run_at <= now:
                    due.append(self._heapq.heappop(self._tasks))
            for task in due:
                try:
                    task.func(*task.args, **task.kwargs)
                except Exception as e:
                    logger.error(f"Task {task.task_id} failed: {e}")
                if task.repeat_interval:
                    task.run_at = time.monotonic() + task.repeat_interval
                    with self._lock:
                        self._heapq.heappush(self._tasks, task)
            time.sleep(0.05)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)


# ─────────────────────────────────────────────
# Validators
# ─────────────────────────────────────────────

def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    pattern = (
        r"^(https?://)"
        r"([a-zA-Z0-9.-]+)"
        r"(:\d+)?"
        r"(/[^\s]*)?"
        r"$"
    )
    return bool(re.match(pattern, url))


def validate_ip_v4(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        n = int(part)
        if n < 0 or n > 255:
            return False
    return True


def validate_credit_card(number: str) -> bool:
    """Luhn algorithm."""
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_phone(phone: str) -> bool:
    pattern = r"^\+?[\d\s\-().]{7,20}$"
    return bool(re.match(pattern, phone))


def validate_password_strength(password: str) -> Dict[str, bool]:
    return {
        "min_length": len(password) >= 8,
        "has_upper": bool(re.search(r"[A-Z]", password)),
        "has_lower": bool(re.search(r"[a-z]", password)),
        "has_digit": bool(re.search(r"\d", password)),
        "has_special": bool(re.search(r"[^a-zA-Z0-9]", password)),
    }


# ─────────────────────────────────────────────
# Date / time utilities
# ─────────────────────────────────────────────

def utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def now_local() -> datetime.datetime:
    return datetime.datetime.now()


def timestamp() -> float:
    return time.time()


def from_timestamp(ts: float) -> datetime.datetime:
    return datetime.datetime.utcfromtimestamp(ts)


def format_datetime(dt: datetime.datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


def parse_datetime(s: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime.datetime:
    return datetime.datetime.strptime(s, fmt)


def add_days(dt: datetime.datetime, days: int) -> datetime.datetime:
    return dt + datetime.timedelta(days=days)


def add_hours(dt: datetime.datetime, hours: int) -> datetime.datetime:
    return dt + datetime.timedelta(hours=hours)


def diff_days(dt1: datetime.datetime, dt2: datetime.datetime) -> int:
    return abs((dt1 - dt2).days)


def start_of_day(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def is_weekend(dt: datetime.datetime) -> bool:
    return dt.weekday() >= 5


def week_number(dt: datetime.datetime) -> int:
    return dt.isocalendar()[1]


# ─────────────────────────────────────────────
# JSON utilities
# ─────────────────────────────────────────────

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def to_json(obj: Any, indent: Optional[int] = None) -> str:
    return json.dumps(obj, cls=DateTimeEncoder, ensure_ascii=False, indent=indent)


def from_json(s: str) -> Any:
    return json.loads(s)


def pretty_json(obj: Any) -> str:
    return to_json(obj, indent=2)


# ─────────────────────────────────────────────
# File utilities
# ─────────────────────────────────────────────

def read_text(path: Union[str, pathlib.Path], encoding: str = "utf-8") -> str:
    return pathlib.Path(path).read_text(encoding=encoding)


def write_text(path: Union[str, pathlib.Path], content: str, encoding: str = "utf-8") -> None:
    pathlib.Path(path).write_text(content, encoding=encoding)


def read_json(path: Union[str, pathlib.Path]) -> Any:
    return json.loads(read_text(path))


def write_json(path: Union[str, pathlib.Path], obj: Any, indent: int = 2) -> None:
    write_text(path, to_json(obj, indent=indent))


def ensure_dir(path: Union[str, pathlib.Path]) -> pathlib.Path:
    p = pathlib.Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_files(
    directory: Union[str, pathlib.Path],
    pattern: str = "*",
    recursive: bool = False,
) -> List[pathlib.Path]:
    p = pathlib.Path(directory)
    if recursive:
        return list(p.rglob(pattern))
    return list(p.glob(pattern))


def file_extension(path: Union[str, pathlib.Path]) -> str:
    return pathlib.Path(path).suffix.lstrip(".")


def file_stem(path: Union[str, pathlib.Path]) -> str:
    return pathlib.Path(path).stem


def file_size(path: Union[str, pathlib.Path]) -> int:
    return pathlib.Path(path).stat().st_size


# ─────────────────────────────────────────────
# Logging helpers
# ─────────────────────────────────────────────

def setup_logging(
    level: str = "INFO",
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs) -> None:
        extra = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
        self._logger.log(level, f"{message} {extra}".strip())

    def debug(self, msg: str, **kwargs) -> None:
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs) -> None:
        self._log(logging.CRITICAL, msg, **kwargs)


# ─────────────────────────────────────────────
# Simple DI container
# ─────────────────────────────────────────────

class DIContainer:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}

    def register(self, name: str, value: Any) -> None:
        self._services[name] = value

    def register_factory(self, name: str, factory: Callable, singleton: bool = False) -> None:
        self._factories[name] = (factory, singleton)

    def resolve(self, name: str) -> Any:
        if name in self._services:
            return self._services[name]
        if name in self._factories:
            factory, is_singleton = self._factories[name]
            if is_singleton:
                if name not in self._singletons:
                    self._singletons[name] = factory(self)
                return self._singletons[name]
            return factory(self)
        raise KeyError(f"Service '{name}' not registered")

    def has(self, name: str) -> bool:
        return name in self._services or name in self._factories

    def remove(self, name: str) -> None:
        self._services.pop(name, None)
        self._factories.pop(name, None)
        self._singletons.pop(name, None)


# ─────────────────────────────────────────────
# Graph utilities
# ─────────────────────────────────────────────

class Graph(Generic[T]):
    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self._adj: Dict[T, Set[T]] = defaultdict(set)
        self._weights: Dict[Tuple[T, T], float] = {}

    def add_vertex(self, vertex: T) -> None:
        if vertex not in self._adj:
            self._adj[vertex] = set()

    def add_edge(self, u: T, v: T, weight: float = 1.0) -> None:
        self._adj[u].add(v)
        self._weights[(u, v)] = weight
        if not self.directed:
            self._adj[v].add(u)
            self._weights[(v, u)] = weight

    def remove_edge(self, u: T, v: T) -> None:
        self._adj[u].discard(v)
        self._weights.pop((u, v), None)
        if not self.directed:
            self._adj[v].discard(u)
            self._weights.pop((v, u), None)

    def neighbors(self, vertex: T) -> Set[T]:
        return self._adj.get(vertex, set())

    def vertices(self) -> List[T]:
        return list(self._adj.keys())

    def edges(self) -> List[Tuple[T, T, float]]:
        return [(u, v, self._weights.get((u, v), 1.0))
                for u, neighbors in self._adj.items()
                for v in neighbors]

    def degree(self, vertex: T) -> int:
        return len(self._adj.get(vertex, set()))

    def has_edge(self, u: T, v: T) -> bool:
        return v in self._adj.get(u, set())

    def vertex_count(self) -> int:
        return len(self._adj)

    def edge_count(self) -> int:
        total = sum(len(n) for n in self._adj.values())
        return total if self.directed else total // 2

    def is_connected(self) -> bool:
        if not self._adj:
            return True
        start = next(iter(self._adj))
        visited = set(bfs(dict(self._adj), start))  # type: ignore
        return len(visited) == len(self._adj)

    def topological_sort(self) -> List[T]:
        if not self.directed:
            raise ValueError("Topological sort requires a directed graph")
        visited: Set[T] = set()
        stack: List[T] = []

        def dfs_topo(v: T) -> None:
            visited.add(v)
            for neighbor in self._adj.get(v, set()):
                if neighbor not in visited:
                    dfs_topo(neighbor)
            stack.append(v)

        for vertex in self.vertices():
            if vertex not in visited:
                dfs_topo(vertex)
        return list(reversed(stack))


# ─────────────────────────────────────────────
# Miscellaneous small utility classes
# ─────────────────────────────────────────────

class Stopwatch:
    def __init__(self) -> None:
        self._start: Optional[float] = None
        self._elapsed: float = 0.0

    def start(self) -> None:
        self._start = time.perf_counter()

    def stop(self) -> float:
        if self._start is None:
            raise RuntimeError("Stopwatch not started")
        self._elapsed += time.perf_counter() - self._start
        self._start = None
        return self._elapsed

    def reset(self) -> None:
        self._start = None
        self._elapsed = 0.0

    def lap(self) -> float:
        if self._start is None:
            return self._elapsed
        return self._elapsed + (time.perf_counter() - self._start)

    def __enter__(self) -> Stopwatch:
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()


class Accumulator(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []

    def add(self, item: T) -> None:
        self._items.append(item)

    def add_many(self, items: Iterable[T]) -> None:
        self._items.extend(items)

    def drain(self) -> List[T]:
        items = list(self._items)
        self._items.clear()
        return items

    def peek(self) -> List[T]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)


class CounterMap(Generic[K]):
    def __init__(self) -> None:
        self._counts: Dict[K, int] = defaultdict(int)

    def increment(self, key: K, amount: int = 1) -> int:
        self._counts[key] += amount
        return self._counts[key]

    def decrement(self, key: K, amount: int = 1) -> int:
        self._counts[key] -= amount
        return self._counts[key]

    def reset(self, key: K) -> None:
        self._counts.pop(key, None)

    def get(self, key: K) -> int:
        return self._counts.get(key, 0)

    def top_n(self, n: int) -> List[Tuple[K, int]]:
        return sorted(self._counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def total(self) -> int:
        return sum(self._counts.values())

    def keys(self):
        return self._counts.keys()

    def __len__(self) -> int:
        return len(self._counts)


class FrozenDict(dict):
    """Immutable dictionary."""

    def __setitem__(self, key, value):
        raise TypeError("FrozenDict is immutable")

    def __delitem__(self, key):
        raise TypeError("FrozenDict is immutable")

    def clear(self):
        raise TypeError("FrozenDict is immutable")

    def pop(self, *args):
        raise TypeError("FrozenDict is immutable")

    def popitem(self):
        raise TypeError("FrozenDict is immutable")

    def setdefault(self, *args):
        raise TypeError("FrozenDict is immutable")

    def update(self, *args, **kwargs):
        raise TypeError("FrozenDict is immutable")

    def __hash__(self):
        return hash(frozenset(self.items()))


class Interval:
    def __init__(self, start: float, end: float, inclusive: bool = True) -> None:
        if start > end:
            raise ValueError("start must be <= end")
        self.start = start
        self.end = end
        self.inclusive = inclusive

    def contains(self, value: float) -> bool:
        if self.inclusive:
            return self.start <= value <= self.end
        return self.start < value < self.end

    def overlaps(self, other: Interval) -> bool:
        return self.start <= other.end and other.start <= self.end

    def length(self) -> float:
        return self.end - self.start

    def midpoint(self) -> float:
        return (self.start + self.end) / 2

    def clamp(self, value: float) -> float:
        return max(self.start, min(self.end, value))

    def __repr__(self) -> str:
        brackets = "[]" if self.inclusive else "()"
        return f"{brackets[0]}{self.start}, {self.end}{brackets[1]}"


class MultiDict(Generic[K, V]):
    """Dictionary that allows multiple values per key."""

    def __init__(self) -> None:
        self._data: Dict[K, List[V]] = defaultdict(list)

    def add(self, key: K, value: V) -> None:
        self._data[key].append(value)

    def get(self, key: K) -> List[V]:
        return list(self._data.get(key, []))

    def get_first(self, key: K) -> Optional[V]:
        items = self._data.get(key, [])
        return items[0] if items else None

    def remove(self, key: K, value: V) -> bool:
        if key in self._data and value in self._data[key]:
            self._data[key].remove(value)
            if not self._data[key]:
                del self._data[key]
            return True
        return False

    def remove_all(self, key: K) -> List[V]:
        return self._data.pop(key, [])

    def keys(self):
        return self._data.keys()

    def all_values(self) -> List[V]:
        return [v for vals in self._data.values() for v in vals]

    def __len__(self) -> int:
        return sum(len(v) for v in self._data.values())

    def __contains__(self, key: K) -> bool:
        return key in self._data


# ─────────────────────────────────────────────
# Entry point for manual testing
# ─────────────────────────────────────────────

def _demo() -> None:
    print("=== Vector2 ===")
    v1 = Vector2(3, 4)
    print(f"magnitude: {v1.magnitude()}, normalized: {v1.normalized()}")

    print("\n=== Sorting ===")
    data = [random.randint(0, 100) for _ in range(10)]
    print(f"original:  {data}")
    print(f"bubble:    {bubble_sort(data)}")
    print(f"merge:     {merge_sort(data)}")
    print(f"quick:     {quick_sort(data)}")

    print("\n=== BST ===")
    bst: BinarySearchTree[int] = BinarySearchTree()
    for n in [5, 3, 7, 1, 4, 6, 8]:
        bst.insert(n)
    print(f"inorder: {bst.inorder()}")
    print(f"height:  {bst.height()}")

    print("\n=== Expression evaluator ===")
    for expr in ["2 + 3 * 4", "(2 + 3) * 4", "10 / (2 + 3)"]:
        print(f"  {expr} = {evaluate_expression(expr)}")

    print("\n=== Rate limiter ===")
    rl = RateLimiter(rate=10, capacity=10)
    print(f"acquired: {rl.acquire(5)}, tokens left: {rl.available_tokens:.1f}")

    print("\n=== Validators ===")
    print(f"email valid: {validate_email('user@example.com')}")
    print(f"url valid:   {validate_url('https://example.com/path')}")
    print(f"ipv4 valid:  {validate_ip_v4('192.168.1.1')}")
    print(f"luhn valid:  {validate_credit_card('4532015112830366')}")

    print("\n=== LRU Cache ===")
    cache: LRUCache[str, int] = LRUCache(3)
    for i, k in enumerate(["a", "b", "c", "d"]):
        cache.put(k, i)
    print(f"cache keys: {list(cache.keys())}")

    print("\n=== Fibonacci ===")
    print(f"first 10: {fibonacci_sequence(10)}")

    print("\n=== Humanize ===")
    print(f"bytes:    {humanize_bytes(1_234_567_890)}")
    print(f"duration: {humanize_duration(3723)}")

    print("\nAll demos passed.")


if __name__ == "__main__":
    setup_logging("INFO")
    _demo()

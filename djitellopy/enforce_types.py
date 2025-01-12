"""
이 파일은 @301_Moved_Permanently의 StackOverflow 게시물을 기반으로 합니다.
참조: https://stackoverflow.com/a/50622643

이 코드는 클래스 자체에 데코레이터를 추가하여 
클래스의 모든 메서드를 래핑할 수 있도록 수정되었습니다.
"""

import inspect
import typing
from contextlib import suppress
from functools import wraps


def _is_unparameterized_special_typing(type_hint):
    # typing.Any, typing.Union, typing.ClassVar(매개변수 없음)와 같은 특수 타입 체크
    if hasattr(typing, "_SpecialForm"):
        return isinstance(type_hint, typing._SpecialForm)
    elif hasattr(type_hint, "__origin__"):
        return type_hint.__origin__ is None
    else:
        return False


def enforce_types(target):
    """모든 멤버 함수에 타입 체크를 추가하는 클래스 데코레이터
    """
    def check_types(spec, *args, **kwargs):
        # 매개변수와 인자를 매핑
        parameters = dict(zip(spec.args, args))
        parameters.update(kwargs)
        for name, value in parameters.items():
            with suppress(KeyError):  # 타입 어노테이션이 없는 매개변수는 모든 타입 허용
                type_hint = spec.annotations[name]
                if _is_unparameterized_special_typing(type_hint):
                    continue

                if hasattr(type_hint, "__origin__") and type_hint.__origin__ is not None:
                    actual_type = type_hint.__origin__
                elif hasattr(type_hint, "__args__") and type_hint.__args__ is not None:
                    actual_type = type_hint.__args__
                else:
                    actual_type = type_hint

                if not isinstance(value, actual_type):
                    raise TypeError("Unexpected type for '{}' (expected {} but found {})"
                                    .format(name, type_hint, type(value)))

    def decorate(func):
        # 함수의 매개변수 정보 가져오기
        spec = inspect.getfullargspec(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            check_types(spec, *args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    if inspect.isclass(target):
        # 클래스인 경우 모든 메서드에 데코레이터 적용
        members = inspect.getmembers(target, predicate=inspect.isfunction)
        for name, func in members:
            setattr(target, name, decorate(func))

        return target
    else:
        # 함수인 경우 해당 함수에만 데코레이터 적용
        return decorate(target)

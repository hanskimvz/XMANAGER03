"""
Custom Exceptions
애플리케이션 전용 예외 클래스를 정의합니다.

서비스 계층에서 발생하는 비즈니스 로직 관련 예외를 처리합니다.
"""

from typing import Any, Optional, Dict


class AppException(Exception):
    """
    애플리케이션 기본 예외 클래스

    모든 커스텀 예외의 부모 클래스입니다.
    """

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 변환"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# ==================== 리소스 관련 예외 ====================

class NotFoundException(AppException):
    """리소스를 찾을 수 없는 경우"""

    def __init__(
        self,
        resource: str,
        resource_id: Any = None,
        message: Optional[str] = None
    ):
        self.resource = resource
        self.resource_id = resource_id
        msg = message or f"{resource}을(를) 찾을 수 없습니다."
        if resource_id:
            msg = f"{resource} (ID: {resource_id})을(를) 찾을 수 없습니다."
        super().__init__(
            message=msg,
            code="NOT_FOUND",
            details={"resource": resource, "id": resource_id}
        )


class AlreadyExistsException(AppException):
    """리소스가 이미 존재하는 경우"""

    def __init__(
        self,
        resource: str,
        field: str = None,
        value: Any = None,
        message: Optional[str] = None
    ):
        self.resource = resource
        msg = message or f"{resource}이(가) 이미 존재합니다."
        if field and value:
            msg = f"{resource}의 {field} '{value}'이(가) 이미 존재합니다."
        super().__init__(
            message=msg,
            code="ALREADY_EXISTS",
            details={"resource": resource, "field": field, "value": value}
        )


class DuplicateException(AlreadyExistsException):
    """중복 데이터 예외 (AlreadyExistsException의 별칭)"""
    pass


# ==================== 검증 관련 예외 ====================

class ValidationException(AppException):
    """데이터 검증 실패"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        errors: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, "errors": errors or {}}
        )


class InvalidOperationException(AppException):
    """유효하지 않은 작업"""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            code="INVALID_OPERATION",
            details={"operation": operation}
        )


# ==================== 비즈니스 로직 예외 ====================

class BusinessRuleException(AppException):
    """비즈니스 규칙 위반"""

    def __init__(self, message: str, rule: Optional[str] = None):
        super().__init__(
            message=message,
            code="BUSINESS_RULE_VIOLATION",
            details={"rule": rule}
        )


class CircularReferenceException(BusinessRuleException):
    """순환 참조 발생 (BOM 등에서 사용)"""

    def __init__(
        self,
        message: str = "순환 참조가 발생했습니다.",
        parent_id: Any = None,
        child_id: Any = None
    ):
        super().__init__(
            message=message,
            rule="NO_CIRCULAR_REFERENCE"
        )
        self.details.update({
            "parent_id": parent_id,
            "child_id": child_id
        })


class DependencyException(BusinessRuleException):
    """의존성으로 인해 작업 불가"""

    def __init__(
        self,
        message: str,
        resource: str,
        dependent_resources: Optional[list] = None
    ):
        super().__init__(message=message, rule="NO_DEPENDENT_RESOURCES")
        self.details.update({
            "resource": resource,
            "dependent_resources": dependent_resources or []
        })


# ==================== 권한 관련 예외 ====================

class UnauthorizedException(AppException):
    """인증 실패"""

    def __init__(self, message: str = "인증이 필요합니다."):
        super().__init__(message=message, code="UNAUTHORIZED")


class ForbiddenException(AppException):
    """권한 부족"""

    def __init__(self, message: str = "접근 권한이 없습니다."):
        super().__init__(message=message, code="FORBIDDEN")


# ==================== 파일 관련 예외 ====================

class FileException(AppException):
    """파일 처리 관련 예외"""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        operation: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="FILE_ERROR",
            details={"filename": filename, "operation": operation}
        )


class FileNotFoundException(FileException):
    """파일을 찾을 수 없음"""

    def __init__(self, filename: str):
        super().__init__(
            message=f"파일을 찾을 수 없습니다: {filename}",
            filename=filename,
            operation="read"
        )
        self.code = "FILE_NOT_FOUND"


class FileSizeExceededException(FileException):
    """파일 크기 초과"""

    def __init__(
        self,
        filename: str,
        max_size: int,
        actual_size: int
    ):
        super().__init__(
            message=f"파일 크기가 제한을 초과했습니다: {filename} ({actual_size} > {max_size})",
            filename=filename,
            operation="upload"
        )
        self.code = "FILE_SIZE_EXCEEDED"
        self.details.update({
            "max_size": max_size,
            "actual_size": actual_size
        })


class InvalidFileTypeException(FileException):
    """허용되지 않은 파일 형식"""

    def __init__(
        self,
        filename: str,
        allowed_types: list,
        actual_type: str
    ):
        super().__init__(
            message=f"허용되지 않은 파일 형식입니다: {actual_type}",
            filename=filename,
            operation="upload"
        )
        self.code = "INVALID_FILE_TYPE"
        self.details.update({
            "allowed_types": allowed_types,
            "actual_type": actual_type
        })


# ==================== 외부 서비스 예외 ====================

class ExternalServiceException(AppException):
    """외부 서비스 오류"""

    def __init__(
        self,
        message: str,
        service_name: str,
        original_error: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            details={
                "service_name": service_name,
                "original_error": original_error
            }
        )


class DatabaseException(AppException):
    """데이터베이스 오류"""

    def __init__(
        self,
        message: str = "데이터베이스 오류가 발생했습니다.",
        original_error: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"original_error": original_error}
        )

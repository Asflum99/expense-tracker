class Result<T> {
  final T? value;
  final Exception? exception;

  Result._(this.value, this.exception);

  static Result<T> success<T>(T value) => Result._(value, null);
  static Result<T> failure<T>(Exception e) => Result._(null, e);

  bool get isSuccess => value != null;
  bool get isFailure => exception != null;

  T? getOrNull() => value;
  Exception? exceptionOrNull() => exception;
}
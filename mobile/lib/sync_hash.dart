import 'dart:convert';

import 'package:crypto/crypto.dart';

dynamic orderedJson(dynamic value) {
  if (value is Map) {
    final keys = value.keys.cast<String>().toList()..sort();
    return {for (final key in keys) key: orderedJson(value[key])};
  }
  if (value is List) return value.map(orderedJson).toList();
  return value;
}

String syncHash(dynamic value) =>
    sha256.convert(utf8.encode(jsonEncode(orderedJson(value)))).toString();

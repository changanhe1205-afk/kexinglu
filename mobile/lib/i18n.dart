import 'package:flutter/material.dart';
import 'ui_messages.dart';

class AppLanguage {
  static String current = 'zh';
  static const names = {'zh': '简体中文', 'zh-TW': '繁體中文', 'en': 'English', 'ja': '日本語'};
  static Locale get locale => current == 'zh-TW' ? const Locale('zh','TW') : Locale(current);
}
String tr(String text) => uiMessages[text]?[AppLanguage.current] ?? text;

/// Only UI labels use this widget. User records continue to use plain Text.
class LocalText extends StatelessWidget {
  final String data;
  final TextStyle? style;
  final TextAlign? textAlign;
  final TextOverflow? overflow;
  final int? maxLines;
  final bool? softWrap;
  final StrutStyle? strutStyle;
  final TextWidthBasis? textWidthBasis;
  final TextHeightBehavior? textHeightBehavior;
  final String? semanticsLabel;
  const LocalText(this.data, {super.key, this.style, this.textAlign, this.overflow,
    this.maxLines, this.softWrap, this.strutStyle, this.textWidthBasis, this.textHeightBehavior, this.semanticsLabel});
  @override Widget build(BuildContext context) {
    Localizations.localeOf(context); // Update even when this widget is const.
    return Text(tr(data), style: style, textAlign: textAlign, overflow: overflow,
      maxLines: maxLines, softWrap: softWrap, strutStyle: strutStyle, textWidthBasis: textWidthBasis,
      textHeightBehavior: textHeightBehavior, semanticsLabel: semanticsLabel);
  }
}

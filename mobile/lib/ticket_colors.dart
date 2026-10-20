import 'package:flutter/material.dart';

// Exact colors from desktop ticket_design.py. Independent of app appearance.
class TicketColors {
  final Color paper, ink, back, backInk;
  const TicketColors(this.paper, this.ink, this.back, this.backInk);
  static const air = <String, List<Color>>{
    'classic': [
      Color(0xfffffefa),
      Color(0xff203b60),
      Color(0xff718095),
      Color(0xffeaf0f7),
    ],
    'minimal': [
      Color(0xffffffff),
      Color(0xff22252b),
      Color(0xff717780),
      Color(0xfff0f1f3),
    ],
    'midnight': [
      Color(0xff192537),
      Color(0xffeef3fc),
      Color(0xffb1c0d6),
      Color(0xff273a53),
    ],
    'rose': [
      Color(0xfffff8f9),
      Color(0xff6d3849),
      Color(0xff9c6f7c),
      Color(0xfff3e0e6),
    ],
    'digital': [
      Color(0xfff8fbff),
      Color(0xff244567),
      Color(0xff708296),
      Color(0xffe4eef8),
    ],
  };
  static const brands = <String, Color>{
    'CA': Color(0xff8d2937),
    'MU': Color(0xff253f70),
    'CZ': Color(0xff176b8b),
    'HU': Color(0xff983d37),
    'MF': Color(0xff245e87),
    '3U': Color(0xff9e3f35),
    'ZH': Color(0xff8c3345),
    'FM': Color(0xff324e77),
    '9C': Color(0xff426f42),
    'HO': Color(0xff89354a),
    'GJ': Color(0xff807047),
    'KN': Color(0xff76425d),
    'GS': Color(0xff925247),
    'SC': Color(0xff365f80),
    'TV': Color(0xff865e49),
    'PN': Color(0xff5d4c7f),
  };
  factory TicketColors.fromData(Map<String, dynamic> data) {
    final desktop = data['_desktop'] as Map? ?? {};
    final rail = data['mode'] == 'rail';
    if (rail) {
      final paper = desktop['vehicle'] == '火车'
          ? const Color(0xfff8e9e7)
          : const Color(0xffe9f3f9);
      return TicketColors(
        paper,
        const Color(0xff25313a),
        paper,
        const Color(0xff25313a),
      );
    }
    final style = '${data['style'] ?? desktop['style'] ?? 'classic'}';
    final colors = air[style] ?? air['classic']!;
    final code = '${data['code'] ?? ''}'.trim().toUpperCase();
    final brand =
        brands[code.length >= 2 ? code.substring(0, 2) : ''] ??
        const Color(0xff37596a);
    final soft = style == 'minimal' || style == 'rose';
    return TicketColors(
      colors[0],
      colors[1],
      soft ? colors[3] : brand,
      soft ? colors[1] : Colors.white,
    );
  }
}

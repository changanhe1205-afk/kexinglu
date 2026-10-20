import 'i18n.dart';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'weather.dart';
import 'atlas.dart';
import 'look.dart';
import 'store.dart';

class JournalHome extends StatefulWidget {
  final JournalStore store;
  final AtlasData atlas;
  final AppPalette palette;
  final VoidCallback onTravel, onTickets, onFood, onMovies, onBooks;
  final Widget? recovery;
  const JournalHome({super.key, required this.store, required this.atlas,
    required this.palette, required this.onTravel, required this.onTickets,
    required this.onFood, required this.onMovies, required this.onBooks, this.recovery});
  @override
  State<JournalHome> createState() => _JournalHomeState();
}

class _JournalHomeState extends State<JournalHome> {
  List<dynamic> quotes = [['千里之行，始于足下。', '老子']];
  int quoteIndex = 0;
  AppPalette get p => widget.palette;

  @override
  void initState() {
    super.initState();
    rootBundle.loadString('assets/quotes.json').then((value) {
      if (mounted) setState(() {quotes = jsonDecode(value);});
    });
  }

  String get greet {
    final h = DateTime.now().hour;
    return h < 5 || h >= 23 ? '夜深了' : h < 9 ? '早上好' : h < 13 ? '中午好' : h < 18 ? '下午好' : '晚上好';
  }

  String get dateLabel {
    final n = DateTime.now();
    return '${n.year}年${n.month}月${n.day}日  星期${'一二三四五六日'[n.weekday - 1]}';
  }

  Widget surface(Widget child) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color: p.paper.withValues(alpha: .84),
      borderRadius: BorderRadius.circular(18), border: Border.all(color: p.ink.withValues(alpha: .08))), child: child);

  Widget shortcut(String label, String hint, IconData icon, VoidCallback action) => Material(
    color: p.paper.withValues(alpha: .82),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18),
      side: BorderSide(color: p.ink.withValues(alpha: .08))),
    child: InkWell(
      onTap: action,
      borderRadius: BorderRadius.circular(18),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: p.accent.withValues(alpha: .10),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, size: 19, color: p.accent),
          ),
          const SizedBox(height: 10),
          LocalText(label, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
          const SizedBox(height: 3),
          LocalText(hint, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 10, color: p.ink.withValues(alpha: .5))),
        ]),
      ),
    ),
  );

  Widget sectionLabel(String kicker, String title) => Row(children: [
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      LocalText(kicker, style: TextStyle(fontSize: 9, letterSpacing: 2.2, fontWeight: FontWeight.w600,
        color: p.accent.withValues(alpha: .78))),
      const SizedBox(height: 6),
      LocalText(title, style: const TextStyle(fontSize: 21, height: 1.1,
        letterSpacing: -.7, fontWeight: FontWeight.w600)),
    ])),
  ]);

  Widget journalEntry() => Material(
    color: p.accent.withValues(alpha: p.dark ? .16 : .08),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(18),
      side: BorderSide(color: p.accent.withValues(alpha: .2)),
    ),
    child: InkWell(
      onTap: widget.onBooks,
      borderRadius: BorderRadius.circular(18),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
        child: Row(children: [
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(color: p.paper, borderRadius: BorderRadius.circular(13)),
            child: Icon(Icons.menu_book_outlined, size: 20, color: p.accent),
          ),
          const SizedBox(width: 13),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const LocalText('旅行手账', style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
            const SizedBox(height: 3),
            LocalText('把一路的页码装订成册', style: TextStyle(fontSize: 10, color: p.ink.withValues(alpha: .5))),
          ])),
          Icon(Icons.chevron_right_rounded, size: 20, color: p.accent.withValues(alpha: .6)),
        ]),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 16, 20, 132),
    children: [
      // 顶部问候：只留时间感，不再用大时钟占版面。
      LocalText('TODAY', style: TextStyle(fontSize: 9, letterSpacing: 2.4,
        fontWeight: FontWeight.w600, color: p.accent.withValues(alpha: .78))),
      const SizedBox(height: 7),
      Text(greet, style: const TextStyle(fontSize: 26, height: 1.1,
        letterSpacing: -.9, fontWeight: FontWeight.w600)),
      const SizedBox(height: 5),
      Text(dateLabel, style: TextStyle(fontSize: 11.5, color: p.ink.withValues(alpha: .55))),
      const SizedBox(height: 18),
      if (widget.recovery != null) ...[widget.recovery!, const SizedBox(height: 12)],
      WeatherPanel(store: widget.store, palette: p),
      const SizedBox(height: 14),
      surface(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        LocalText('每日一句', style: TextStyle(fontSize: 12, color: p.ink.withValues(alpha: .6))),
        const SizedBox(height: 12),
        LocalText('${quotes[quoteIndex][0]}', style: const TextStyle(fontSize: 16, height: 1.5)),
        Row(children: [
          Expanded(child: LocalText('— ${quotes[quoteIndex][1]}',
            style: TextStyle(fontSize: 12, color: p.ink.withValues(alpha: .6)))),
          TextButton(
            onPressed: () => setState(() {quoteIndex = (quoteIndex + 1) % quotes.length;}),
            child: const LocalText('换一句'),
          ),
        ]),
      ])),
      const SizedBox(height: 26),
      sectionLabel('QUICK NOTES', '记录此刻'),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: shortcut('旅行日志', '地点与故事', Icons.luggage_outlined, widget.onTravel)),
        const SizedBox(width: 12),
        Expanded(child: shortcut('旅程票根', '机票与车票', Icons.confirmation_number_outlined, widget.onTickets)),
      ]),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: shortcut('食光小记', '一餐一味', Icons.restaurant_outlined, widget.onFood)),
        const SizedBox(width: 12),
        Expanded(child: shortcut('影视收藏', '电影与剧', Icons.movie_filter_outlined, widget.onMovies)),
      ]),
      const SizedBox(height: 14),
      journalEntry(),
    ],
  );
}

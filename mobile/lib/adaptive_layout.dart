import 'package:flutter/material.dart';

/// Respond to available window width, including Android split-screen windows.
class JournalWorkspace extends StatelessWidget {
  final List<Widget> children;
  final int mapIndex;
  const JournalWorkspace({super.key, required this.children, required this.mapIndex});

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, size) {
    if (size.maxWidth < 900 || size.maxHeight < 500) {
      return ListView(padding: const EdgeInsets.only(bottom: 130), children: children);
    }
    return Padding(
      key: const ValueKey('tablet-map-workspace'),
      padding: EdgeInsets.only(top: 12, bottom: 112 + MediaQuery.viewPaddingOf(context).bottom),
      child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        SizedBox(width: (size.maxWidth * .42).clamp(360.0, 520.0),
          child: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
            for (var i = 0; i < children.length; i++) if (i != mapIndex) children[i],
          ])),
        Expanded(child: SizedBox.expand(child: children[mapIndex])),
      ]),
    );
  });
}

class JournalDashboard extends StatelessWidget {
  final List<Widget> children;
  final int splitIndex;
  const JournalDashboard({super.key, required this.children, required this.splitIndex});
  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, size) {
    final wide = size.maxWidth >= 900;
    return ListView(padding: EdgeInsets.fromLTRB(wide ? 24 : 20, wide ? 24 : 16, wide ? 24 : 20, 132), children: wide ? [
      Row(key: const ValueKey('tablet-home-columns'), crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch,
            children: children.take(splitIndex).toList())),
          const SizedBox(width: 28),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch,
            children: children.skip(splitIndex).toList())),
        ]),
    ] : children);
  });
}

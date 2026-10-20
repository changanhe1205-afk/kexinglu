import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Ed25519 RFC 8032 public test vector (not a service credential)', () async {
    const seedHex = '9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60';
    const expectPub = 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a';
    final seed = [
      for (var i = 0; i + 1 < seedHex.length; i += 2)
        int.parse(seedHex.substring(i, i + 2), radix: 16),
    ];
    final keyPair = await Ed25519().newKeyPairFromSeed(seed);
    final pub = await keyPair.extractPublicKey();
    final pubHex = pub.bytes
        .map((b) => b.toRadixString(16).padLeft(2, '0'))
        .join();
    expect(pubHex, expectPub);
  });
}

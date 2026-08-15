# Vizual materiallar

## social-card.svg → GitHub sosial önizləməsi

GitHub **SVG qəbul etmir** — PNG lazımdır (1280×640, ≤1 MB).

Codespace-də və ya Linux-da:

```bash
sudo apt-get install -y librsvg2-bin
rsvg-convert -w 1280 -h 640 docs/assets/social-card.svg -o docs/assets/social-card.png
```

Alternativ (heç nə quraşdırmadan): SVG-ni brauzerdə aç, ekran görüntüsü al.

Sonra: **GitHub → Settings → General → Social preview → Upload an image**.

## Rəqəmlər sənədlə eyni olmalıdır

Kartdakı `91.4%`, `19 fields`, `214 tests` rəqəmləri
[docs/POSITIONING.md](../POSITIONING.md)-dəki sübutlu iddialar cədvəlindən gəlir.
Ölçmə yenilənəndə **hər ikisi** dəyişməlidir — kart köhnə rəqəmlə qalsa, mövqe
sənədinin əsas qaydası pozulur: *sübutu olmayan iddia heç bir yerdə yazılmır.*

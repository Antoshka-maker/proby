<?php
declare(strict_types=1);

function head(array $o): void
{
    $site = (string)cfg('site_name');
    $title = $o['title'] ?? $site;
    $full = ($o['title'] ?? '') !== '' && $o['title'] !== $site ? $o['title'] . ' — ' . $site : $site;
    $desc = $o['desc'] ?? (string)cfg('lead');
    $url = site_url() . ($o['path'] ?? '/');
    $img = $o['image'] ?? (site_url() . '/og/_site.png');
    $ym = preg_replace('~\D~', '', (string)cfg('metrika_id'));
    ?><!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title><?= h($full) ?></title>
<meta name="description" content="<?= h($desc) ?>">
<link rel="canonical" href="<?= h($url) ?>">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#faf8f4" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#15161a" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="<?= isset($o['article']) ? 'article' : 'website' ?>">
<meta property="og:site_name" content="<?= h($site) ?>">
<meta property="og:title" content="<?= h($title) ?>">
<meta property="og:description" content="<?= h($desc) ?>">
<meta property="og:url" content="<?= h($url) ?>">
<meta property="og:image" content="<?= h($img) ?>">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="ru_RU">
<meta name="twitter:card" content="summary_large_image">
<?php if (!empty($o['noindex'])): ?><meta name="robots" content="noindex"><?php endif ?>
<link rel="preload" href="/assets/fonts/pt-serif-cyrillic-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="<?= asset('style.css') ?>">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<?php if ($ym !== ''): ?>
<script>(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();for(var j=0;j<document.scripts.length;j++){if(document.scripts[j].src===r){return;}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
ym(<?= $ym ?>,"init",{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true});</script>
<?php endif ?>
<script>window.YM_ID=<?= $ym !== '' ? $ym : 'null' ?>;</script>
</head>
<body class="<?= h($o['body'] ?? '') ?>">
<?php
}

function foot(bool $withReader = false): void
{
    $tg = (string)cfg('telegram');
    $ym = preg_replace('~\D~', '', (string)cfg('metrika_id'));
    ?>
<footer class="foot w">
  <nav>
    <a href="/">Все новеллы</a>
    <a href="/ob-avtore">Об авторе</a>
    <?php if ($tg !== '' && $tg !== 'https://t.me/'): ?><a href="<?= h($tg) ?>" data-goal="tg_click" rel="noopener">Telegram</a><?php endif ?>
  </nav>
  <p><span class="age">18+</span> © <?= date('Y') ?> <?= h((string)cfg('author')) ?> · <a href="/privacy">Конфиденциальность</a></p>
</footer>
<div class="cookie" id="cookie" hidden>
  <span>Сайт использует cookie Яндекс Метрики. <a href="/privacy">Подробнее</a></span>
  <button type="button" id="cookie-ok">Понятно</button>
</div>
<script src="<?= asset('site.js') ?>" defer></script>
<?php if ($ym !== ''): ?><noscript><div><img src="https://mc.yandex.ru/watch/<?= $ym ?>" style="position:absolute;left:-9999px" alt=""></div></noscript><?php endif ?>
</body>
</html>
<?php
}

function topbar(string $left, string $right = ''): void
{
    echo '<div class="top">' . $left . '<span class="top-r">' . $right . '</span></div>';
}

function render_blocks(array $blocks): void
{
    $first = true;
    foreach ($blocks as $b) {
        if ($b['type'] === 'sep') { echo "<div class=\"sep\" aria-hidden=\"true\">* * *</div>\n"; $first = false; continue; }
        $cls = [];
        if ($first) $cls[] = 'first';
        if (!empty($b['dialog'])) $cls[] = 'd';
        echo '<p' . ($cls ? ' class="' . implode(' ', $cls) . '"' : '') . '>' . $b['html'] . "</p>\n";
        $first = false;
    }
}

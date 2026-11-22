<?php
declare(strict_types=1);
require __DIR__ . '/inc/lib.php';
require __DIR__ . '/inc/view.php';

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$path = '/' . trim(rawurldecode($path), '/');

header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: strict-origin-when-cross-origin');

if ($path === '/send') { require __DIR__ . '/inc/send.php'; exit; }
if (preg_match('~^/og/([a-z0-9_-]+)\.png$~', $path, $m)) { require __DIR__ . '/inc/og.php'; og_serve($m[1]); exit; }
if ($path === '/admin' || str_starts_with($path, '/admin/')) { require __DIR__ . '/inc/admin.php'; exit; }

header('Content-Type: text/html; charset=utf-8');

if ($path === '/') { page_home(); exit; }
if ($path === '/ob-avtore') { page_static('ob-avtore', 'Об авторе'); exit; }
if ($path === '/privacy') { page_privacy(); exit; }

$slug = ltrim($path, '/');
$list = novellas();
foreach ($list as $i => $n) {
    if ($n['slug'] === $slug) { page_novella($list, $i); exit; }
}
// старые адреса из админки (скрытые новеллы видны по прямой ссылке только с ?preview)
if (isset($_GET['preview'])) {
    $all = novellas(true);
    foreach ($all as $i => $n) if ($n['slug'] === $slug) { page_novella($all, $i, true); exit; }
}
page_404();

function page_home(): void
{
    $list = novellas();
    head(['path' => '/', 'body' => 'home']);
    ?>
<main class="w">
<?php topbar('<span class="brand">' . h((string)cfg('author')) . '</span>', '<a href="/ob-avtore">Об авторе</a>'); ?>
<h1 class="home-h"><?= h((string)cfg('site_name')) ?></h1>
<p class="lead"><?= para_html(typo((string)cfg('lead'))) ?></p>
<div class="cards">
<?php foreach ($list as $i => $n): ?>
<a class="card" href="/<?= h($n['slug']) ?>">
  <span class="card-m"><?= $i + 1 ?> · <?= minutes_label($n['minutes']) ?></span>
  <b><?= h($n['title']) ?></b>
  <i>«<?= str_replace(NBSP, '&nbsp;', h(trim($n['first'], '«»'))) ?>»</i>
</a>
<?php endforeach ?>
<?php if (!$list): ?><p class="empty">Скоро здесь появятся новеллы</p><?php endif ?>
</div>
</main>
<?php
    foot();
}

function page_novella(array $list, int $i, bool $preview = false): void
{
    $n = $list[$i];
    $next = $list[$i + 1] ?? null;
    $tg = (string)cfg('telegram');
    $desc = minutes_label($n['minutes']) . ' чтения. ' . $n['first'];
    head([
        'title' => $n['title'],
        'desc' => $desc,
        'path' => '/' . $n['slug'],
        'image' => site_url() . '/og/' . $n['slug'] . '.png?v=' . $n['mtime'],
        'article' => true,
        'body' => 'read',
        'noindex' => $preview,
    ]);
    ?>
<div class="bar" id="bar" aria-hidden="true"></div>
<main class="w">
<?php topbar('<a href="/">← Все новеллы</a>', ($i + 1) . ' из ' . count($list)); ?>
<article id="text" data-slug="<?= h($n['slug']) ?>" data-min="<?= (int)$n['minutes'] ?>">
<h1><?= h($n['title']) ?></h1>
<div class="meta"><?= minutes_label($n['minutes']) ?> чтения</div>
<?php render_blocks($n['blocks']); ?>
<div id="end" aria-hidden="true"></div>
</article>

<section class="after">
<form class="fb" id="fb" method="post" action="/send">
  <h2>Дочитали? Пара слов автору</h2>
  <div class="ch" role="radiogroup" aria-label="Как вам новелла">
    <label><input type="radio" name="mood" value="Зацепило"><span>Зацепило</span></label>
    <label><input type="radio" name="mood" value="Нормально"><span>Нормально</span></label>
    <label><input type="radio" name="mood" value="Не моё"><span>Не моё</span></label>
  </div>
  <label class="sr" for="fb-text">Что запомнилось</label>
  <textarea id="fb-text" name="text" maxlength="2000" rows="3" placeholder="Что запомнилось? Анонимно, без почты и имени"></textarea>
  <input type="text" name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
  <input type="hidden" name="novella" value="<?= h($n['slug']) ?>">
  <input type="hidden" name="t" value="">
  <button type="submit" class="btn">Отправить</button>
  <p class="fb-ok" hidden>Спасибо! Автор прочитает</p>
  <p class="fb-err" hidden>Не отправилось. Попробуйте ещё раз чуть позже</p>
</form>

<?php if ($tg !== '' && $tg !== 'https://t.me/'): ?>
<a class="tg" href="<?= h($tg) ?>" data-goal="tg_click" rel="noopener">Новые новеллы — в Telegram-канале →</a>
<?php endif ?>

<?php if ($next): ?>
<a class="next" href="/<?= h($next['slug']) ?>" data-goal="next_click"><small>Следующая новелла · <?= minutes_label($next['minutes']) ?></small><?= h($next['title']) ?></a>
<?php else: ?>
<a class="next" href="/"><small>Это последняя новелла</small>Ко всем новеллам</a>
<?php endif ?>
</section>
</main>
<?php
    foot(true);
}

function page_static(string $name, string $title): void
{
    $blocks = page_text($name);
    head(['title' => $title, 'path' => '/' . $name, 'body' => 'read']);
    ?>
<main class="w">
<?php topbar('<a href="/">← Все новеллы</a>'); ?>
<article class="page">
<h1><?= h($title) ?></h1>
<?php $blocks ? render_blocks($blocks) : print('<p class="first">Текст скоро появится</p>'); ?>
</article>
</main>
<?php
    foot();
}

function page_privacy(): void
{
    $op = (string)cfg('operator');
    $mail = (string)cfg('contact_email');
    $site = site_url();
    head(['title' => 'Политика конфиденциальности', 'path' => '/privacy', 'body' => 'doc']);
    ?>
<main class="w">
<?php topbar('<a href="/">← Все новеллы</a>'); ?>
<article class="page doc">
<h1>Политика конфиденциальности</h1>
<p>Сайт <?= h($site) ?> публикует литературные тексты. Здесь описано, какие данные о&nbsp;посетителях собираются и&nbsp;зачем.</p>
<h2>Кто отвечает за данные</h2>
<p><?= $op !== '' ? h($op) : 'Владелец сайта' ?><?= $mail !== '' ? ', почта для обращений: <a href="mailto:' . h($mail) . '">' . h($mail) . '</a>' : '' ?>.</p>
<h2>Что собирается</h2>
<p>Сайт не просит имя, телефон или почту и не ведёт учётных записей.</p>
<p><b>Яндекс Метрика.</b> Сервис ООО «Яндекс» собирает обезличенные сведения: какие страницы открыты, как далеко прокручен текст, с какого сайта пришёл посетитель, тип устройства и браузера, примерное место по IP-адресу. Метрика записывает действия на странице (Вебвизор) и хранит cookie в браузере. Эти данные нужны, чтобы понимать, какие новеллы дочитывают, и делать сайт удобнее. Условия Яндекса: <a href="https://yandex.ru/legal/metrica_termsofuse/" rel="noopener">yandex.ru/legal/metrica_termsofuse</a>.</p>
<p><b>Форма отзыва.</b> Отзыв анонимный: отправляется только выбранный ответ, текст, который вы сами написали, и название новеллы. IP-адрес не сохраняется. Не пишите в отзыве личные данные, если не хотите, чтобы их прочитал автор.</p>
<h2>Cookie</h2>
<p>Cookie Метрики помогают отличать новые визиты от повторных. Отключить их можно в настройках браузера, сайт продолжит работать. Плашку о cookie сайт запоминает в браузере, чтобы не показывать её снова.</p>
<h2>Передача данных</h2>
<p>Данные не продаются и не передаются третьим лицам, кроме ООО «Яндекс» (Метрика) и Telegram, через который автору приходят отзывы.</p>
<h2>Как связаться</h2>
<p>По вопросам о данных пишите <?= $mail !== '' ? 'на <a href="mailto:' . h($mail) . '">' . h($mail) . '</a>' : 'владельцу сайта' ?>. Продолжая пользоваться сайтом, вы соглашаетесь с этой политикой.</p>
<p class="muted">Редакция от <?= date('d.m.Y', filemtime(__FILE__)) ?></p>
</article>
</main>
<?php
    foot();
}

function page_404(): void
{
    http_response_code(404);
    head(['title' => 'Страница не найдена', 'path' => '/', 'noindex' => true]);
    ?>
<main class="w">
<?php topbar('<a href="/">← Все новеллы</a>'); ?>
<h1>Такой страницы нет</h1>
<p class="lead">Возможно, новеллу переименовали. <a href="/">Все новеллы</a></p>
</main>
<?php
    foot();
}

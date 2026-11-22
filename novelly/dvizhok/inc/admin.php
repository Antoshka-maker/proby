<?php
declare(strict_types=1);
// Простая админка: загрузить новеллу файлом, порядок, скрыть, заменить, отзывы, настройки.

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
header('X-Frame-Options: DENY');

$secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
session_name('adm');
session_set_cookie_params(['lifetime' => 86400 * 30, 'path' => '/admin', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Strict']);
session_start();

$authFile = DATA_DIR . '/admin.json';
$auth = is_file($authFile) ? (json_decode((string)file_get_contents($authFile), true) ?: []) : [];

function adm_redirect(string $msg = ''): void
{
    if ($msg !== '') $_SESSION['flash'] = $msg;
    header('Location: /admin');
    exit;
}

function adm_csrf(): string
{
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(16));
    return $_SESSION['csrf'];
}

function adm_page_start(string $title): void
{
    ?><!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title><?= h($title) ?></title>
<style>
:root{--bg:#f6f5f2;--fg:#222;--mut:#777;--line:#ddd;--acc:#9a3b2e;--card:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#141518;--fg:#ddd;--mut:#999;--line:#30323a;--acc:#de9277;--card:#1c1e24}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.w{max-width:760px;margin:0 auto;padding:18px 16px 60px}h1{font-size:22px;margin:6px 0 16px}h2{font-size:18px;margin:28px 0 10px}
.box{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
input[type=text],input[type=password],input[type=url],input[type=email],textarea{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--fg);font:inherit}
textarea{min-height:140px}label{display:block;font-size:14px;color:var(--mut);margin:10px 0 4px}
button,.b{display:inline-block;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:9px;padding:8px 12px;font:inherit;font-size:14px;cursor:pointer;text-decoration:none}
button.p{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600;padding:11px 16px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.mut{color:var(--mut);font-size:14px}
.n{display:grid;grid-template-columns:1fr auto;gap:6px 12px;align-items:start}.n b{font-size:17px}
.flash{background:#e7f3e7;color:#225522;border-radius:10px;padding:10px 14px;margin-bottom:14px}@media(prefers-color-scheme:dark){.flash{background:#1f3322;color:#bfe3c4}}
.hid{opacity:.55}code{font-size:13px;word-break:break-all}form.in{display:inline}
.top{display:flex;justify-content:space-between;align-items:center}
details summary{cursor:pointer;color:var(--acc)}
</style></head><body><div class="w">
<?php
}

// ---------- вход ----------
if (!$auth) {
    adm_page_start('Админка');
    echo '<h1>Админка выключена</h1><p>Пароль ещё не задан. Создайте файл data/admin.json командой из инструкции.</p></div></body></html>';
    exit;
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$logged = !empty($_SESSION['ok']) && ($_SESSION['ver'] ?? '') === ($auth['ver'] ?? '');

if (!$logged) {
    $err = '';
    if ($method === 'POST' && isset($_POST['password'])) {
        $rlFile = CACHE_DIR . '/login.json';
        $rl = is_file($rlFile) ? (json_decode((string)file_get_contents($rlFile), true) ?: []) : [];
        $rl = array_values(array_filter($rl, fn($t) => $t > time() - 900));
        if (count($rl) >= 8) $err = 'Слишком много попыток, подождите 15 минут';
        elseif (password_verify((string)$_POST['password'], (string)$auth['hash'])) {
            session_regenerate_id(true);
            $_SESSION['ok'] = 1;
            $_SESSION['ver'] = $auth['ver'] ?? '';
            adm_redirect();
        } else {
            $rl[] = time();
            @file_put_contents($rlFile, json_encode($rl));
            $err = 'Неверный пароль';
        }
    }
    adm_page_start('Вход');
    ?>
<h1>Вход в админку</h1>
<form method="post" class="box"><label for="pw">Пароль</label><input id="pw" type="password" name="password" autocomplete="current-password" autofocus>
<?php if ($err): ?><p style="color:#c0392b"><?= h($err) ?></p><?php endif ?>
<p><button class="p">Войти</button></p></form></div></body></html>
<?php
    exit;
}

// ---------- действия ----------
function files_ordered(): array
{
    $files = glob(NOV_DIR . '/*.{docx,txt,md}', GLOB_BRACE) ?: [];
    $files = array_values(array_filter($files, fn($f) => basename($f)[0] !== '_' && basename($f)[0] !== '~'));
    natcasesort($files);
    return array_values($files);
}

function sidecar(string $f): string { return preg_replace('~\.(docx|txt|md)$~i', '.json', $f); }

function meta_get(string $f): array { $s = sidecar($f); return is_file($s) ? (json_decode((string)file_get_contents($s), true) ?: []) : []; }
function meta_set(string $f, array $m): void { file_put_contents(sidecar($f), json_encode($m, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT)); }

// переименовать все файлы по порядку: 01-..., 02-...
function renumber(array $files): void
{
    $tmp = [];
    foreach ($files as $i => $f) {
        $base = preg_replace('~^\d+[\s._-]*~u', '', pathinfo($f, PATHINFO_FILENAME));
        $ext = pathinfo($f, PATHINFO_EXTENSION);
        $newBase = sprintf('%02d-%s', $i + 1, $base);
        $t = NOV_DIR . '/~tmp' . $i . '.' . $ext;
        rename($f, $t);
        $side = []; foreach (['json', 'jpg', 'jpeg', 'png', 'webp'] as $e) { $o = NOV_DIR . '/' . pathinfo($f, PATHINFO_FILENAME) . '.' . $e; if (is_file($o)) { rename($o, NOV_DIR . "/~tmp$i.$e"); $side[] = $e; } }
        $tmp[] = [$t, $newBase, $ext, $side, $i];
    }
    foreach ($tmp as [$t, $newBase, $ext, $side, $i]) {
        rename($t, NOV_DIR . "/$newBase.$ext");
        foreach ($side as $e) rename(NOV_DIR . "/~tmp$i.$e", NOV_DIR . "/$newBase.$e");
    }
}

function check_upload(array $u): string
{
    if (($u['error'] ?? 1) !== UPLOAD_ERR_OK) return 'Файл не загрузился';
    if ($u['size'] > 15 * 1024 * 1024) return 'Файл больше 15 МБ';
    $ext = strtolower(pathinfo((string)$u['name'], PATHINFO_EXTENSION));
    if (!in_array($ext, ['docx', 'txt', 'md'], true)) return 'Нужен файл .docx или .txt (документ Word или текст)';
    if ($ext === 'docx') {
        $z = new ZipArchive();
        if ($z->open($u['tmp_name']) !== true || $z->locateName('word/document.xml') === false) return 'Файл не похож на документ Word (.docx). Если это .doc, пересохраните его как .docx';
        $z->close();
    }
    return '';
}

if ($method === 'POST') {
    if (!hash_equals(adm_csrf(), (string)($_POST['csrf'] ?? ''))) adm_redirect('Страница устарела, повторите действие');
    $a = (string)($_POST['a'] ?? '');
    $files = files_ordered();
    $idx = isset($_POST['i']) ? (int)$_POST['i'] : -1;
    $f = $files[$idx] ?? null;

    if ($a === 'logout') { session_destroy(); header('Location: /admin'); exit; }

    if ($a === 'upload') {
        $u = $_FILES['file'] ?? [];
        if ($e = check_upload($u)) adm_redirect($e);
        $ext = strtolower(pathinfo((string)$u['name'], PATHINFO_EXTENSION));
        $title = trim((string)($_POST['title'] ?? ''));
        $tmp = NOV_DIR . '/~upload-' . bin2hex(random_bytes(4)) . '.' . $ext;
        move_uploaded_file($u['tmp_name'], $tmp);
        $m = [];
        if ($title !== '') $m['title'] = $title;
        if (!empty($_POST['hidden'])) $m['hidden'] = true;
        $n = parse_novella($tmp);
        if (!$n) { unlink($tmp); adm_redirect('В файле не нашлось текста'); }
        // адрес страницы: из названия (поле формы или первая строка файла)
        $slug = slugify($title !== '' ? $title : $n['title']);
        $existing = array_map(fn($x) => preg_replace('~^\d+[\s._-]*~u', '', pathinfo($x, PATHINFO_FILENAME)), $files);
        $s = $slug; $k = 2; while (in_array($s, $existing, true)) $s = $slug . '-' . $k++;
        $dest = NOV_DIR . sprintf('/%02d-%s.%s', count($files) + 1, $s, $ext);
        rename($tmp, $dest);
        if ($m) meta_set($dest, $m);
        $n = parse_novella($dest);
        adm_redirect('Новелла «' . $n['title'] . '» добавлена: ' . minutes_label($n['minutes']) . ' чтения' . (!empty($m['hidden']) ? ', пока скрыта' : ''));
    }

    if ($a === 'settings') {
        $keys = ['site_name', 'author', 'lead', 'site_url', 'telegram', 'metrika_id', 'tg_bot_token', 'tg_chat_id', 'feedback_email', 'operator', 'contact_email'];
        $set = [];
        foreach ($keys as $k) $set[$k] = trim((string)($_POST[$k] ?? ''));
        $set['metrika_id'] = preg_replace('~\D~', '', $set['metrika_id']);
        $set['site_url'] = rtrim($set['site_url'], '/');
        file_put_contents(DATA_DIR . '/settings.json', json_encode($set, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        foreach (glob(CACHE_DIR . '/og-*.png') ?: [] as $x) @unlink($x);
        adm_redirect('Настройки сохранены');
    }
    if ($a === 'about') {
        file_put_contents(ROOT . '/content/ob-avtore.txt', str_replace("\r\n", "\n", (string)($_POST['text'] ?? '')));
        adm_redirect('Страница «Об авторе» сохранена');
    }
    if ($a === 'testbot') {
        $token = (string)cfg('tg_bot_token'); $chat = (string)cfg('tg_chat_id');
        if ($token === '' || $chat === '') adm_redirect('Сначала впишите токен бота и chat_id в настройках');
        $ch = curl_init('https://api.telegram.org/bot' . $token . '/sendMessage');
        curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => http_build_query(['chat_id' => $chat, 'text' => 'Проверка: отзывы с сайта будут приходить сюда']), CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 8]);
        $res = json_decode((string)curl_exec($ch), true); curl_close($ch);
        adm_redirect(!empty($res['ok']) ? 'Бот отправил проверочное сообщение' : 'Бот не смог отправить: ' . ($res['description'] ?? 'нет связи с Telegram') . '. Напишите боту /start и проверьте chat_id');
    }
    if ($a === 'password') {
        $p1 = (string)($_POST['p1'] ?? ''); $p2 = (string)($_POST['p2'] ?? '');
        if (mb_strlen($p1) < 8) adm_redirect('Пароль должен быть не короче 8 символов');
        if ($p1 !== $p2) adm_redirect('Пароли не совпали');
        $ver = bin2hex(random_bytes(4));
        file_put_contents($GLOBALS['authFile'], json_encode(['hash' => password_hash($p1, PASSWORD_DEFAULT), 'ver' => $ver]));
        $_SESSION['ver'] = $ver;
        adm_redirect('Пароль изменён, на других устройствах нужно войти заново');
    }

    if (!$f) adm_redirect();

    if ($a === 'up' || $a === 'down') {
        $j = $a === 'up' ? $idx - 1 : $idx + 1;
        if (isset($files[$j])) { [$files[$idx], $files[$j]] = [$files[$j], $files[$idx]]; renumber($files); }
        adm_redirect();
    }
    if ($a === 'toggle') { $m = meta_get($f); $m['hidden'] = empty($m['hidden']); meta_set($f, $m); adm_redirect($m['hidden'] ? 'Скрыта с сайта' : 'Опубликована'); }
    if ($a === 'meta') {
        $m = meta_get($f);
        $t = trim((string)($_POST['title'] ?? '')); $fs = trim((string)($_POST['first'] ?? ''));
        if ($t !== '') $m['title'] = $t; else unset($m['title']);
        if ($fs !== '') $m['first'] = $fs; else unset($m['first']);
        meta_set($f, $m);
        adm_redirect('Сохранено');
    }
    if ($a === 'replace') {
        $u = $_FILES['file'] ?? [];
        if ($e = check_upload($u)) adm_redirect($e);
        $ext = strtolower(pathinfo((string)$u['name'], PATHINFO_EXTENSION));
        $dest = NOV_DIR . '/' . pathinfo($f, PATHINFO_FILENAME) . '.' . $ext;
        if ($dest !== $f) { @rename(sidecar($f), sidecar($dest)); unlink($f); }
        move_uploaded_file($u['tmp_name'], $dest);
        adm_redirect('Текст заменён, адрес страницы прежний');
    }
    if ($a === 'cover') {
        $u = $_FILES['file'] ?? [];
        $ext = strtolower(pathinfo((string)($u['name'] ?? ''), PATHINFO_EXTENSION));
        if (($u['error'] ?? 1) !== UPLOAD_ERR_OK || !in_array($ext, ['jpg', 'jpeg', 'png'], true) || !@getimagesize($u['tmp_name'])) adm_redirect('Нужна картинка .jpg или .png');
        $base = NOV_DIR . '/' . pathinfo($f, PATHINFO_FILENAME);
        foreach (['jpg', 'jpeg', 'png', 'webp'] as $e) @unlink("$base.$e");
        move_uploaded_file($u['tmp_name'], "$base.$ext");
        touch($f);
        adm_redirect('Картинка для превью загружена');
    }
    if ($a === 'nocover') {
        $base = NOV_DIR . '/' . pathinfo($f, PATHINFO_FILENAME);
        foreach (['jpg', 'jpeg', 'png', 'webp'] as $e) @unlink("$base.$e");
        touch($f);
        adm_redirect('Своя картинка убрана, превью рисуется автоматически');
    }
    if ($a === 'delete') {
        @mkdir(ROOT . '/content/korzina');
        $base = pathinfo($f, PATHINFO_FILENAME);
        foreach (glob(NOV_DIR . '/' . $base . '.*') ?: [] as $x) rename($x, ROOT . '/content/korzina/' . date('Ymd-His-') . basename($x));
        renumber(files_ordered());
        adm_redirect('Удалена (копия в папке content/korzina)');
    }
    adm_redirect();
}

// ---------- страница админки ----------
$all = novellas(true);
$files = files_ordered();
$flash = $_SESSION['flash'] ?? ''; unset($_SESSION['flash']);
$csrf = adm_csrf();
$base = site_url();
$set = cfg();
adm_page_start('Админка — ' . (string)cfg('site_name'));
$hiddenInputs = fn(int $i = -1) => '<input type="hidden" name="csrf" value="' . h($csrf) . '">' . ($i >= 0 ? '<input type="hidden" name="i" value="' . $i . '">' : '');
// сопоставляем разобранные новеллы с файлами по имени файла
$byFile = []; foreach ($all as $n) $byFile[$n['file']] = $n;
?>
<div class="top"><h1>Админка</h1><form method="post" class="in"><?= $hiddenInputs() ?><input type="hidden" name="a" value="logout"><button>Выйти</button></form></div>
<?php if ($flash): ?><div class="flash"><?= h($flash) ?></div><?php endif ?>

<h2>Добавить новеллу</h2>
<form method="post" enctype="multipart/form-data" class="box">
<?= $hiddenInputs() ?><input type="hidden" name="a" value="upload">
<label for="f">Файл Word (.docx) или текст (.txt). Первая строка файла — название</label>
<input id="f" type="file" name="file" accept=".docx,.txt,.md" required>
<label for="t">Название, если в файле его нет (необязательно)</label>
<input id="t" type="text" name="title" maxlength="120">
<label class="row" style="color:inherit;flex-wrap:nowrap"><input type="checkbox" name="hidden" value="1"> Пока не показывать на сайте (посмотреть сначала самому)</label>
<p><button class="p">Загрузить</button></p>
<p class="mut">Кавычки, тире, неразрывные пробелы, время чтения и картинка для Telegram появятся сами. Новелла встанет последней в списке</p>
</form>

<h2>Новеллы (<?= count($files) ?>)</h2>
<?php foreach ($files as $i => $f):
    $n = $byFile[basename($f)] ?? null;
    if (!$n) continue;
    $url = $base . '/' . $n['slug'];
    $utm = $url . '?utm_source=telegram&utm_medium=channel&utm_campaign=novelly&utm_content=' . $n['slug'];
    $m = meta_get($f);
?>
<div class="box <?= $n['hidden'] ? 'hid' : '' ?>">
  <div class="n">
    <div><span class="mut"><?= $i + 1 ?> · <?= minutes_label($n['minutes']) ?> · <?= number_format($n['words'], 0, ',', ' ') ?> слов<?= $n['hidden'] ? ' · <b>скрыта</b>' : '' ?></span><br><b><?= h($n['title']) ?></b></div>
    <div class="row">
      <form method="post" class="in"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="up"><button <?= $i === 0 ? 'disabled' : '' ?> title="Выше">↑</button></form>
      <form method="post" class="in"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="down"><button <?= $i === count($files) - 1 ? 'disabled' : '' ?> title="Ниже">↓</button></form>
    </div>
  </div>
  <p class="row" style="margin:10px 0 6px">
    <a class="b" href="/<?= h($n['slug']) ?><?= $n['hidden'] ? '?preview=1' : '' ?>" target="_blank">Открыть</a>
    <button type="button" onclick="navigator.clipboard.writeText(this.dataset.u);this.textContent='Скопировано'" data-u="<?= h($utm) ?>">Ссылка для канала</button>
    <form method="post" class="in"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="toggle"><button><?= $n['hidden'] ? 'Опубликовать' : 'Скрыть' ?></button></form>
  </p>
  <details><summary>Ещё: название, первая фраза, замена текста, картинка, удаление</summary>
    <form method="post"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="meta">
      <label>Название (пусто = из файла)</label><input type="text" name="title" value="<?= h($m['title'] ?? '') ?>" placeholder="<?= h($n['title']) ?>">
      <label>Первая фраза для карточки и превью (пусто = первое предложение текста)</label><input type="text" name="first" value="<?= h($m['first'] ?? '') ?>" placeholder="<?= h($n['first']) ?>">
      <p><button>Сохранить</button></p></form>
    <form method="post" enctype="multipart/form-data"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="replace">
      <label>Заменить текст новым файлом (адрес страницы не изменится)</label><input type="file" name="file" accept=".docx,.txt,.md" required> <button>Заменить</button></form>
    <form method="post" enctype="multipart/form-data"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="cover">
      <label>Своя картинка для превью в Telegram, 1200×630 (иначе рисуется сама)</label><input type="file" name="file" accept=".jpg,.jpeg,.png" required> <button>Загрузить</button></form>
    <p class="row"><a class="b" href="/og/<?= h($n['slug']) ?>.png?v=<?= time() ?>" target="_blank">Посмотреть превью</a>
      <form method="post" class="in"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="nocover"><button>Убрать свою картинку</button></form>
      <form method="post" class="in" onsubmit="return confirm('Удалить новеллу «<?= h(addslashes($n['title'])) ?>»? Файл попадёт в корзину на хостинге')"><?= $hiddenInputs($i) ?><input type="hidden" name="a" value="delete"><button>Удалить</button></form></p>
    <p class="mut">Ссылка с метками: <code><?= h($utm) ?></code></p>
  </details>
</div>
<?php endforeach ?>

<h2>Отзывы</h2>
<div class="box">
<?php
$csv = DATA_DIR . '/otzyvy.csv';
$rows = [];
if (is_file($csv) && ($fh = fopen($csv, 'r'))) { fgetcsv($fh, 0, ';'); while (($r = fgetcsv($fh, 0, ';')) !== false) $rows[] = $r; fclose($fh); }
$rows = array_reverse($rows);
if (!$rows) echo '<p class="mut">Пока нет</p>';
foreach (array_slice($rows, 0, 50) as $r): ?>
  <p><span class="mut"><?= h($r[0] ?? '') ?> · <?= h($r[1] ?? '') ?></span><?= ($r[2] ?? '') !== '' ? ' · <b>' . h($r[2]) . '</b>' : '' ?><?= ($r[3] ?? '') !== '' ? '<br>' . nl2br(h($r[3])) : '' ?></p>
<?php endforeach ?>
<?php if (count($rows) > 50): ?><p class="mut">Показаны последние 50 из <?= count($rows) ?></p><?php endif ?>
</div>

<h2>Об авторе</h2>
<form method="post" class="box"><?= $hiddenInputs() ?><input type="hidden" name="a" value="about">
<textarea name="text" rows="8"><?= h(is_file(ROOT . '/content/ob-avtore.txt') ? (string)file_get_contents(ROOT . '/content/ob-avtore.txt') : '') ?></textarea>
<p class="mut">Каждый абзац с новой строки. Типографика расставится сама</p><p><button class="p">Сохранить</button></p></form>

<h2>Настройки</h2>
<form method="post" class="box"><?= $hiddenInputs() ?><input type="hidden" name="a" value="settings">
<?php
$fields = [
  'site_name' => 'Название цикла', 'author' => 'Псевдоним автора', 'lead' => 'Пара строк о цикле на главной',
  'site_url' => 'Адрес сайта, например https://example.ru', 'telegram' => 'Ссылка на Telegram-канал',
  'metrika_id' => 'Номер счётчика Яндекс Метрики', 'tg_bot_token' => 'Токен бота для отзывов (от @BotFather)',
  'tg_chat_id' => 'Ваш chat_id в Telegram (куда слать отзывы)', 'feedback_email' => 'Почта для копии отзывов (необязательно)',
  'operator' => 'Для политики конфиденциальности: ФИО или «Владелец сайта»', 'contact_email' => 'Почта для обращений по данным',
];
foreach ($fields as $k => $label): ?>
<label for="s-<?= $k ?>"><?= h($label) ?></label>
<?php if ($k === 'lead'): ?><textarea id="s-lead" name="lead" rows="2" style="min-height:70px"><?= h((string)($set[$k] ?? '')) ?></textarea>
<?php else: ?><input id="s-<?= $k ?>" type="<?= $k === 'tg_bot_token' ? 'password' : 'text' ?>" name="<?= $k ?>" value="<?= h((string)($set[$k] ?? '')) ?>" autocomplete="off"><?php endif ?>
<?php endforeach ?>
<p><button class="p">Сохранить настройки</button></p></form>
<form method="post" class="in"><?= $hiddenInputs() ?><input type="hidden" name="a" value="testbot"><button>Проверить бота: прислать тестовое сообщение</button></form>

<h2>Пароль</h2>
<form method="post" class="box"><?= $hiddenInputs() ?><input type="hidden" name="a" value="password">
<label>Новый пароль (от 8 символов)</label><input type="password" name="p1" autocomplete="new-password">
<label>Ещё раз</label><input type="password" name="p2" autocomplete="new-password">
<p><button>Сменить пароль</button></p></form>
</div></body></html>

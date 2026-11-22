<?php
declare(strict_types=1);
// Приём анонимного отзыва: Telegram-бот и/или почта, копия в data/otzyvy.csv

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function out(bool $ok, string $err = ''): void
{
    if (!$ok) http_response_code(400);
    echo json_encode(['ok' => $ok, 'error' => $err], JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') out(false, 'method');
// ловушка для ботов
if (!empty($_POST['website'])) out(true);
// форма должна провисеть на странице хотя бы 3 секунды
$t = (int)($_POST['t'] ?? 0);
if ($t > 0 && $t < 3000) out(true);

$moods = ['Зацепило', 'Нормально', 'Не моё'];
$mood = in_array($_POST['mood'] ?? '', $moods, true) ? $_POST['mood'] : '';
$text = trim((string)($_POST['text'] ?? ''));
$text = mb_substr(preg_replace('~[\x00-\x08\x0B\x0C\x0E-\x1F]~u', '', $text), 0, 2000);
$slug = preg_replace('~[^a-z0-9-]~', '', (string)($_POST['novella'] ?? ''));
if ($mood === '' && $text === '') out(false, 'empty');

// не больше 8 отзывов в час с одного адреса; адрес хранится только как хеш с суточной солью
$rlFile = CACHE_DIR . '/rl.json';
$rl = is_file($rlFile) ? (json_decode((string)file_get_contents($rlFile), true) ?: []) : [];
$now = time();
$key = substr(hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . date('Y-m-d') . __DIR__), 0, 16);
$rl = array_filter($rl, fn($v) => is_array($v) && $v[1] > $now - 3600);
$rl[$key] = isset($rl[$key]) ? [$rl[$key][0] + 1, $rl[$key][1]] : [1, $now];
@file_put_contents($rlFile, json_encode($rl), LOCK_EX);
if ($rl[$key][0] > 8) out(false, 'rate');

$title = $slug;
foreach (novellas(true) as $n) if ($n['slug'] === $slug) { $title = $n['title']; break; }

$msg = "Отзыв: «{$title}»\n" . ($mood !== '' ? "Оценка: {$mood}\n" : '') . ($text !== '' ? "\n{$text}" : '');

// копия в файл (папка data закрыта от посетителей)
$csv = DATA_DIR . '/otzyvy.csv';
$new = !is_file($csv);
if ($fh = @fopen($csv, 'a')) {
    if ($new) fwrite($fh, "\xEF\xBB\xBF");
    if ($new) fputcsv($fh, ['Дата', 'Новелла', 'Оценка', 'Текст'], ';');
    fputcsv($fh, [date('Y-m-d H:i'), $title, $mood, $text], ';');
    fclose($fh);
}

$sent = false;
$token = (string)cfg('tg_bot_token');
$chat = (string)cfg('tg_chat_id');
if ($token !== '' && $chat !== '') {
    $ch = curl_init('https://api.telegram.org/bot' . $token . '/sendMessage');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query(['chat_id' => $chat, 'text' => $msg, 'disable_web_page_preview' => 'true']),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 8,
    ]);
    $res = curl_exec($ch);
    $sent = $res !== false && (json_decode((string)$res, true)['ok'] ?? false);
    curl_close($ch);
}
$mail = (string)cfg('feedback_email');
if ($mail !== '') {
    $host = preg_replace('~[^a-z0-9.-]~i', '', $_SERVER['HTTP_HOST'] ?? 'localhost');
    $subj = '=?UTF-8?B?' . base64_encode('Отзыв: ' . $title) . '?=';
    $ok = @mail($mail, $subj, $msg, "From: noreply@{$host}\r\nContent-Type: text/plain; charset=UTF-8");
    $sent = $sent || $ok;
}
// даже если бот и почта не настроены, отзыв лежит в data/otzyvy.csv и виден в админке
out(true);

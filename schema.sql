-- もしmessagesテーブルが存在していたら削除する
DROP TABLE IF EXISTS messages;

-- messagesテーブルを作成する
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, -- 投稿ごとに自動で番号が振られるID
  board_name TEXT NOT NULL,           -- 掲示板の名前 (general, techなど)nullは空白なし
  text TEXT NOT NULL,                   -- 投稿内容
  sender TEXT NOT NULL,                 -- 投稿者のID
  time TEXT NOT NULL,
  reply_to_id INTEGER
);
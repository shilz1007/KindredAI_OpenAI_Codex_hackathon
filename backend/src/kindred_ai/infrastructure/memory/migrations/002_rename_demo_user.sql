UPDATE memory_users
SET preferred_name = 'Anita'
WHERE id = 'demo-user';

UPDATE memories
SET content = REPLACE(content, 'Amina', 'Anita')
WHERE user_id = 'demo-user';

UPDATE conversation_history
SET content = REPLACE(content, 'Amina', 'Anita')
WHERE user_id = 'demo-user';

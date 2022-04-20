up:
	docker-compose -f memowotoru/docker-compose.yml up -d
	docker-compose -f memowotoru_patched/docker-compose.yml up -d
	docker-compose -f gameserver.yml up -d
	
stop:
	docker-compose -f memowotoru/docker-compose.yml stop
	docker-compose -f memowotoru_patched/docker-compose.yml stop
	docker-compose -f gameserver.yml stop


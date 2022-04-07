# memowotoru

This is an attack-defense-CTF-like training exercise; there is:

- a dockerized vulnerable service, which is ```memowotoru```;
- the patched service, which is ```memowotoru_patched``` (in the folder there is also a writeup which discusses the vulnerabilities & weaknesses of the service);
- the exploit scripts with a stub for flag submission, in ```exploits``` folder;
- a checker for the service, in the ```checker``` folder, developed using [checklib](https://github.com/pomo-mondreganto/checklib).

The idea was to use [this](https://github.com/pomo-mondreganto/ForcAD) gameserver, but it had many issues, so we made a more modest arrangement and left here the checker for reference to write an equivalent checker for another platform.


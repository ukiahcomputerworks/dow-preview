const button = document.querySelector('.menu-button');
const nav = document.querySelector('#site-nav');
document.querySelectorAll('.practice-list details[open], .openings details[open]').forEach((detail) => {
  detail.removeAttribute('open');
});
button?.addEventListener('click', () => {
  const open = button.getAttribute('aria-expanded') === 'true';
  button.setAttribute('aria-expanded', String(!open));
  nav.classList.toggle('open', !open);
});
nav?.addEventListener('click', (event) => {
  if (event.target.matches('a')) {
    nav.classList.remove('open');
    button?.setAttribute('aria-expanded', 'false');
  }
});

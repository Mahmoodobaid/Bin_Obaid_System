// interactive.js - رسائل ذكية وتفاعلية للمستخدم
let currentUser = null;
let pageGuideShown = false;

async function loadCurrentUser() {
    try {
        currentUser = await apiRequest('/admin/profile');
        return currentUser;
    } catch(e) { return null; }
}

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 5) return 'تهجدك مبارك';
    if (hour < 12) return 'صباح الخير';
    if (hour < 14) return 'سعيدة صباحاً';
    if (hour < 18) return 'مساء الخير';
    return 'مساء النور';
}

async function showWelcomeMessage() {
    const user = await loadCurrentUser();
    if (!user) return;
    const name = user.full_name || user.email.split('@')[0];
    const greeting = getGreeting();
    const message = `${greeting}، ${name} 👋<br>أهلاً بك في منظومة بن عبيد. نتمنى لك يوماً موفقاً!`;
    // عرض الرسالة في مكان مناسب (يمكن إضافتها في أعلى كل صفحة)
    const existingDiv = document.getElementById('dynamicWelcome');
    if (existingDiv) existingDiv.remove();
    const welcomeDiv = document.createElement('div');
    welcomeDiv.id = 'dynamicWelcome';
    welcomeDiv.className = 'alert alert-success rounded-4 shadow-sm mb-4';
    welcomeDiv.innerHTML = `<i class="fas fa-smile-wink fa-2x me-3"></i><span>${message}</span>`;
    const mainContent = document.querySelector('.main-content');
    if (mainContent && mainContent.firstChild) mainContent.insertBefore(welcomeDiv, mainContent.firstChild);
}

async function showPageGuide(pageName, description) {
    if (pageGuideShown) return;
    const user = await loadCurrentUser();
    const name = user ? (user.full_name || user.email.split('@')[0]) : 'مديرنا';
    const guideDiv = document.createElement('div');
    guideDiv.className = 'alert alert-info rounded-4 shadow-sm mb-4';
    guideDiv.innerHTML = `<i class="fas fa-info-circle fa-2x me-3"></i>
                          <div><strong>📘 دليل ${pageName}</strong><br>مرحباً بك يا ${name}، ${description}</div>
                          <button type="button" class="btn-close float-end" onclick="this.parentElement.remove()"></button>`;
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        const firstChild = mainContent.firstChild;
        if (firstChild && firstChild.id !== 'dynamicWelcome') mainContent.insertBefore(guideDiv, firstChild);
        else if (firstChild) mainContent.insertBefore(guideDiv, firstChild.nextSibling);
        else mainContent.appendChild(guideDiv);
    }
    pageGuideShown = true;
    setTimeout(() => { if(guideDiv) guideDiv.remove(); }, 15000);
}

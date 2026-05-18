(function () {
    "use strict";

    const triggerSelector = ".js-register-trigger";
    const popupName = "teklink_account_window";
    const popupFeatures = "width=560,height=860,left=220,top=120,resizable=yes,scrollbars=yes";

    const storageKeys = {
        token: "teklink_access_token",
        user: "teklink_current_user",
        cart: "teklink_cart",
    };

    const deliveryOptions = {
        nova: {
            label: "Нова Пошта (відділення)",
            price: 89,
            courierName: "Nova Poshta",
        },
        courier: {
            label: "Кур'єр по місту",
            price: 149,
            courierName: "City Courier",
        },
        pickup: {
            label: "Самовивіз із магазину",
            price: 0,
            courierName: null,
        },
    };

    const productImageRules = [
        {
            keywords: ["acer", "ноут", "laptop", "macbook", "lenovo", "asus vivobook"],
            image: "https://content2.rozetka.com.ua/goods/images/big_tile/633098034.jpg",
        },
        {
            keywords: ["samsung", "iphone", "смартф", "phone", "xiaomi", "galaxy"],
            image: "https://content2.rozetka.com.ua/goods/images/big_tile/653651261.jpg",
        },
        {
            keywords: ["навуш", "headphone", "earbuds", "audio"],
            image: "https://content2.rozetka.com.ua/goods/images/big_tile/614940179.jpg",
        },
        {
            keywords: ["комп'ютер", "pc", "gaming", "desktop", "artline"],
            image: "picture/553474576.webp",
        },
        {
            keywords: ["монітор", "monitor", "display"],
            image: "picture/419088411.webp",
        },
        {
            keywords: ["клавіат", "keyboard"],
            image: "picture/1.webp",
        },
        {
            keywords: ["playstation", "ps5", "приставка", "console"],
            image: "picture/2.webp",
        },
        {
            keywords: ["миша", "mouse"],
            image: "picture/3.webp",
        },
        {
            keywords: ["материн", "motherboard"],
            image: "picture/4.webp",
        },
        {
            keywords: ["відеокарта", "gpu", "rtx", "geforce"],
            image: "picture/5.webp",
        },
        {
            keywords: ["оператив", "ram", "memory"],
            image: "picture/6.webp",
        },
        {
            keywords: ["ssd", "накопичувач", "disk", "drive"],
            image: "picture/7.webp",
        },
    ];

    const fallbackImages = [
        "picture/1.webp",
        "picture/2.webp",
        "picture/3.webp",
        "picture/4.webp",
        "picture/5.webp",
        "picture/6.webp",
        "picture/7.webp",
        "picture/8.webp",
        "picture/419088411.webp",
        "picture/553474576.webp",
        "picture/652545867.webp",
    ];

    const state = {
        user: readStorageJson(storageKeys.user, null),
        sellerAnalytics: null,
        products: [],
        slideCards: [],
        slideOrders: [],
        currentSlideIndex: 0,
        currentSearch: "",
        catalogStatus: {
            message: "",
            tone: "info",
        },
    };

    function readStorageJson(key, fallbackValue) {
        try {
            const rawValue = window.localStorage.getItem(key);
            if (!rawValue) {
                return fallbackValue;
            }
            return JSON.parse(rawValue);
        } catch (error) {
            return fallbackValue;
        }
    }

    function writeStorageJson(key, value) {
        window.localStorage.setItem(key, JSON.stringify(value));
    }

    function getToken() {
        return window.localStorage.getItem(storageKeys.token) || "";
    }

    function isAuthenticated() {
        return Boolean(getToken());
    }

    function setToken(token) {
        if (token) {
            window.localStorage.setItem(storageKeys.token, token);
            return;
        }
        window.localStorage.removeItem(storageKeys.token);
    }

    function clearAuthState() {
        setToken("");
        window.localStorage.removeItem(storageKeys.user);
        state.user = null;
        state.sellerAnalytics = null;
        updateAuthUi();
    }

    function decodeBase64Url(input) {
        const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
        const paddingLength = (4 - (normalized.length % 4)) % 4;
        const padded = normalized + "=".repeat(paddingLength);
        const binary = window.atob(padded);
        const bytes = Uint8Array.from(binary, function (character) {
            return character.charCodeAt(0);
        });
        return new TextDecoder().decode(bytes);
    }

    function parseJwtPayload(token) {
        if (!token || token.split(".").length < 2) {
            return null;
        }

        try {
            return JSON.parse(decodeBase64Url(token.split(".")[1]));
        } catch (error) {
            return null;
        }
    }

    function getCurrentCustomerId() {
        if (state.user && Number.isFinite(Number(state.user.CustomerID))) {
            return Number(state.user.CustomerID);
        }

        const payload = parseJwtPayload(getToken());
        const customerId = payload ? Number(payload.customer_id) : NaN;
        return Number.isFinite(customerId) && customerId > 0 ? customerId : null;
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function (character) {
            const entities = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            };
            return entities[character] || character;
        });
    }

    function normalizeText(value) {
        return String(value || "").trim().toLowerCase();
    }

    function roundMoney(value) {
        return Number((Number(value) || 0).toFixed(2));
    }

    function delay(milliseconds) {
        return new Promise(function (resolve) {
            window.setTimeout(resolve, milliseconds);
        });
    }

    function formatPrice(value) {
        const numericValue = Number(value) || 0;
        const hasFraction = Math.abs(numericValue % 1) > 0.001;
        return (
            new Intl.NumberFormat("uk-UA", {
                minimumFractionDigits: hasFraction ? 2 : 0,
                maximumFractionDigits: 2,
            }).format(numericValue) + "₴"
        );
    }

    function resolveProductImage(name, seed) {
        const normalizedName = normalizeText(name);

        for (const rule of productImageRules) {
            if (rule.keywords.some(function (keyword) {
                return normalizedName.includes(keyword);
            })) {
                return rule.image;
            }
        }

        const index = Math.abs(Number(seed) || 0) % fallbackImages.length;
        return fallbackImages[index];
    }

    function normalizeCartItem(item) {
        if (!item) {
            return null;
        }

        const productId = Number(item.productId);
        if (!Number.isFinite(productId) || productId <= 0) {
            return null;
        }

        const quantity = Math.max(1, Number(item.quantity) || 1);
        const price = roundMoney(item.price);
        const availableQuantity = Number(item.availableQuantity);

        return {
            productId: productId,
            name: String(item.name || "Товар"),
            price: price,
            quantity: quantity,
            image: String(item.image || resolveProductImage(item.name || "", productId)),
            availableQuantity: Number.isFinite(availableQuantity) && availableQuantity >= 0
                ? availableQuantity
                : null,
        };
    }

    function getCart() {
        return readStorageJson(storageKeys.cart, [])
            .map(normalizeCartItem)
            .filter(Boolean);
    }

    function setCart(cart) {
        const normalizedCart = cart.map(normalizeCartItem).filter(Boolean);
        writeStorageJson(storageKeys.cart, normalizedCart);
        updateCartBadges();
    }

    function getCartCount() {
        return getCart().reduce(function (sum, item) {
            return sum + item.quantity;
        }, 0);
    }

    function getCartSubtotal(cart) {
        return cart.reduce(function (sum, item) {
            return sum + roundMoney(item.price * item.quantity);
        }, 0);
    }

    function ensureToastHost() {
        let host = document.querySelector(".js-toast-host");
        if (host) {
            return host;
        }

        host = document.createElement("div");
        host.className = "js-toast-host";
        host.style.position = "fixed";
        host.style.right = "18px";
        host.style.bottom = "18px";
        host.style.zIndex = "9999";
        host.style.display = "flex";
        host.style.flexDirection = "column";
        host.style.gap = "10px";
        host.style.maxWidth = "320px";
        document.body.appendChild(host);
        return host;
    }

    function showToast(message, tone) {
        if (!message) {
            return;
        }

        const host = ensureToastHost();
        const toast = document.createElement("div");
        toast.textContent = message;
        toast.style.padding = "12px 14px";
        toast.style.borderRadius = "12px";
        toast.style.boxShadow = "0 12px 26px rgba(0, 0, 0, 0.16)";
        toast.style.fontSize = "14px";
        toast.style.lineHeight = "1.45";
        toast.style.color = "#ffffff";
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        toast.style.transition = "opacity 0.18s ease, transform 0.18s ease";

        const toneMap = {
            success: "#14824d",
            error: "#be3c3c",
            warning: "#c57d00",
            info: "#1868c7",
        };

        toast.style.backgroundColor = toneMap[tone || "info"] || toneMap.info;
        host.appendChild(toast);

        window.requestAnimationFrame(function () {
            toast.style.opacity = "1";
            toast.style.transform = "translateY(0)";
        });

        window.setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            window.setTimeout(function () {
                toast.remove();
            }, 220);
        }, 3200);
    }

    function createHeaders(headers, includeAuth) {
        const resolvedHeaders = new Headers(headers || {});

        if (includeAuth) {
            const token = getToken();
            if (token) {
                resolvedHeaders.set("Authorization", "Bearer " + token);
            }
        }

        if (!resolvedHeaders.has("Accept")) {
            resolvedHeaders.set("Accept", "application/json");
        }

        return resolvedHeaders;
    }

    async function apiRequest(path, options) {
        const requestOptions = options || {};
        const headers = createHeaders(requestOptions.headers, requestOptions.auth !== false);
        const config = {
            method: requestOptions.method || "GET",
            headers: headers,
        };

        if (requestOptions.body !== undefined) {
            if (
                requestOptions.body instanceof FormData
                || requestOptions.body instanceof URLSearchParams
                || typeof requestOptions.body === "string"
            ) {
                config.body = requestOptions.body;
            } else {
                headers.set("Content-Type", "application/json");
                config.body = JSON.stringify(requestOptions.body);
            }
        }

        const response = await window.fetch(path, config);
        const contentType = response.headers.get("content-type") || "";
        let payload = null;

        if (contentType.includes("application/json")) {
            payload = await response.json();
        } else {
            payload = await response.text();
        }

        if (!response.ok) {
            const message = payload && typeof payload === "object"
                ? payload.detail || payload.message || ("HTTP " + response.status)
                : String(payload || ("HTTP " + response.status));

            if (response.status === 401) {
                clearAuthState();
            }

            const error = new Error(message);
            error.status = response.status;
            throw error;
        }

        return payload;
    }

    async function loadCurrentUser() {
        if (!isAuthenticated()) {
            state.user = null;
            state.sellerAnalytics = null;
            updateAuthUi();
            return null;
        }

        const customerId = getCurrentCustomerId();
        if (!customerId) {
            clearAuthState();
            return null;
        }

        try {
            const user = await apiRequest("/customer/" + customerId);
            state.user = user;
            writeStorageJson(storageKeys.user, user);
            await loadSellerAnalytics({
                silent: true,
            });
            updateAuthUi();
            prefillCheckoutForm();
            return user;
        } catch (error) {
            clearAuthState();
            showToast("Сесію завершено. Увійдіть ще раз.", "warning");
            return null;
        }
    }

    async function loginUser(username, password) {
        const formData = new URLSearchParams();
        formData.set("username", username);
        formData.set("password", password);

        const response = await apiRequest("/login", {
            method: "POST",
            body: formData,
            auth: false,
        });

        setToken(response.access_token || "");
        await loadCurrentUser();
        await syncDynamicData({
            silentCartSync: true,
        });
    }

    async function registerUser(payload) {
        const params = new URLSearchParams();
        params.set("username", payload.username);
        params.set("email", payload.email);
        params.set("password", payload.password);
        params.set("role", payload.role === "seller" ? "seller" : "user");

        if (payload.phone) {
            params.set("phone", payload.phone);
        }
        if (payload.country) {
            params.set("country", payload.country);
        }

        await apiRequest("/register?" + params.toString(), {
            method: "POST",
            auth: false,
        });

        await loginUser(payload.username, payload.password);
    }

    async function loadSellerAnalytics(options) {
        const config = options || {};

        if (!isAuthenticated()) {
            state.sellerAnalytics = null;
            return null;
        }

        try {
            const summary = await apiRequest("/analytics/seller/summary");
            const topProducts = await apiRequest("/analytics/seller/top-products?limit=5");
            state.sellerAnalytics = {
                summary: summary,
                topProducts: Array.isArray(topProducts) ? topProducts : [],
            };
            return state.sellerAnalytics;
        } catch (error) {
            state.sellerAnalytics = null;

            if (error.status === 403) {
                return null;
            }

            if (!config.silent) {
                showToast("Не вдалося завантажити статистику продавця: " + error.message, "warning");
            }

            return null;
        }
    }

    function getAccountTypeLabel() {
        return state.sellerAnalytics ? "продавець" : "користувач";
    }

    function createSellerStatsMarkup() {
        if (!state.sellerAnalytics || !state.sellerAnalytics.summary) {
            return "";
        }

        const summary = state.sellerAnalytics.summary;
        const topProducts = Array.isArray(state.sellerAnalytics.topProducts)
            ? state.sellerAnalytics.topProducts
            : [];

        const topProductsMarkup = topProducts.length
            ? topProducts.map(function (product) {
                return `
                    <li>
                        <strong>${escapeHtml(product.ProductName)}</strong>
                        <span>${product.SoldUnits} шт. • ${formatPrice(product.SalesAmount)}</span>
                    </li>
                `;
            }).join("")
            : '<li><span>Продажів поки ще немає, але аналітика вже готова до роботи.</span></li>';

        return `
            <section class="seller-stats">
                <div class="seller-stats__header">
                    <h2>Статистика продавця</h2>
                    <button class="ghost-btn" type="button" id="refreshStatsBtn">Оновити статистику</button>
                </div>
                <div class="seller-stats__grid">
                    <article class="seller-stats__card">
                        <strong>${summary.OwnedProductsCount}</strong>
                        <span>Товарів у вашому каталозі</span>
                    </article>
                    <article class="seller-stats__card">
                        <strong>${summary.SoldUnits}</strong>
                        <span>Проданих одиниць</span>
                    </article>
                    <article class="seller-stats__card">
                        <strong>${formatPrice(summary.SalesAmount)}</strong>
                        <span>Сума продажів</span>
                    </article>
                    <article class="seller-stats__card">
                        <strong>${summary.OrdersWithSales}</strong>
                        <span>Замовлень із продажами</span>
                    </article>
                </div>
                <div class="seller-stats__statuses">
                    <span>Pending: ${summary.PendingOrders}</span>
                    <span>Completed: ${summary.CompletedOrders}</span>
                    <span>Shipped: ${summary.ShippedOrders}</span>
                    <span>Cancelled: ${summary.CancelledOrders}</span>
                </div>
                <div class="seller-stats__top">
                    <h3>Топ товарів</h3>
                    <ul>${topProductsMarkup}</ul>
                </div>
            </section>
        `;
    }

    function createPopupMarkup() {
        if (state.user) {
            return createAccountPopupMarkup();
        }

        return createGuestPopupMarkup();
    }

    function createGuestPopupMarkup() {
        return `<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Авторизація TekLink</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 18px;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #f5f6f8 0%, #eaeef3 100%);
            color: #1d1d1f;
        }
        .auth-card {
            width: 100%;
            max-width: 460px;
            background: #ffffff;
            border-radius: 18px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.14);
            border: 1px solid #d8dce2;
            padding: 24px;
        }
        h1 {
            margin: 0 0 8px;
            font-size: 28px;
        }
        .intro {
            margin: 0 0 18px;
            color: #5a6370;
            line-height: 1.5;
            font-size: 15px;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }
        .tab-btn {
            flex: 1;
            border: 1px solid #cfd7e3;
            border-radius: 12px;
            background: #f4f7fb;
            color: #30445f;
            padding: 10px 12px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        }
        .tab-btn.is-active {
            background: #0fa6ff;
            border-color: #0fa6ff;
            color: #ffffff;
        }
        .panel[hidden] {
            display: none;
        }
        .field {
            margin-bottom: 13px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-size: 14px;
            font-weight: 700;
        }
        input {
            width: 100%;
            border: 1px solid #cad3df;
            border-radius: 11px;
            padding: 11px 12px;
            font-size: 15px;
            outline: none;
        }
        input:focus {
            border-color: #0fa6ff;
            box-shadow: 0 0 0 3px rgba(15, 166, 255, 0.16);
        }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 8px;
        }
        .submit-btn,
        .secondary-btn {
            flex: 1;
            border: none;
            border-radius: 11px;
            padding: 12px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        }
        .submit-btn {
            background: #0fa6ff;
            color: #ffffff;
        }
        .submit-btn:hover {
            background: #008fdc;
        }
        .secondary-btn {
            background: #eef2f6;
            color: #2e3d50;
        }
        .status {
            min-height: 22px;
            margin-bottom: 12px;
            font-size: 13px;
            line-height: 1.45;
        }
        .status[data-tone="error"] { color: #c03434; }
        .status[data-tone="success"] { color: #177047; }
        .status[data-tone="info"] { color: #2563eb; }
        .helper {
            margin: 12px 0 0;
            padding: 12px;
            border-radius: 12px;
            background: #f4f8fd;
            color: #43566f;
            font-size: 13px;
            line-height: 1.45;
        }
        .field-caption {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 700;
        }
        .role-list {
            display: grid;
            gap: 10px;
        }
        .role-option {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            border: 1px solid #cad3df;
            border-radius: 12px;
            padding: 12px;
            background: #f8fbff;
            cursor: pointer;
        }
        .role-option input {
            width: auto;
            margin-top: 3px;
            flex: 0 0 auto;
        }
        .role-option strong {
            display: block;
            margin-bottom: 4px;
            font-size: 15px;
            color: #243447;
        }
        .role-option small {
            display: block;
            color: #5d6d82;
            line-height: 1.45;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <section class="auth-card">
        <h1>Акаунт TekLink</h1>
        <p class="intro">Увійдіть або створіть обліковий запис, щоб підвантажити товари з бази даних, оформлювати замовлення через API й, за потреби, працювати як продавець.</p>

        <div class="tabs">
            <button class="tab-btn is-active" type="button" data-auth-view-button="login">Вхід</button>
            <button class="tab-btn" type="button" data-auth-view-button="register">Реєстрація</button>
        </div>

        <div class="status" id="authStatus" data-tone="info"></div>

        <section class="panel" data-auth-view="login">
            <form id="loginForm" novalidate>
                <div class="field">
                    <label for="loginName">Ім'я користувача</label>
                    <input id="loginName" name="username" type="text" placeholder="Введіть ваше ім'я" autocomplete="username" required>
                </div>
                <div class="field">
                    <label for="loginPassword">Пароль</label>
                    <input id="loginPassword" name="password" type="password" placeholder="Ваш пароль" autocomplete="current-password" required>
                </div>
                <div class="actions">
                    <button class="submit-btn" type="submit">Увійти</button>
                    <button class="secondary-btn" type="button" data-switch-view="register">Створити акаунт</button>
                </div>
            </form>
        </section>

        <section class="panel" data-auth-view="register" hidden>
            <form id="registerForm" novalidate>
                <div class="field">
                    <label for="regName">Ім'я</label>
                    <input id="regName" name="username" type="text" placeholder="Як вас звати" autocomplete="name" required>
                </div>
                <div class="field">
                    <label for="regEmail">Email</label>
                    <input id="regEmail" name="email" type="email" placeholder="name@example.com" autocomplete="email" required>
                </div>
                <div class="field">
                    <label for="regPhone">Телефон</label>
                    <input id="regPhone" name="phone" type="tel" placeholder="+380..." autocomplete="tel">
                </div>
                <div class="field">
                    <label for="regCountry">Країна</label>
                    <input id="regCountry" name="country" type="text" placeholder="Україна" autocomplete="country-name">
                </div>
                <div class="field">
                    <label for="regPassword">Пароль</label>
                    <input id="regPassword" name="password" type="password" placeholder="Мінімум 6 символів" minlength="6" autocomplete="new-password" required>
                </div>
                <div class="field">
                    <span class="field-caption">Тип акаунта</span>
                    <div class="role-list">
                        <label class="role-option" for="roleCustomer">
                            <input id="roleCustomer" name="role" type="radio" value="user" checked>
                            <span>
                                <strong>Користувач</strong>
                                <small>Покупець, який переглядає каталог, додає товари в кошик та оформлює замовлення.</small>
                            </span>
                        </label>
                        <label class="role-option" for="roleSeller">
                            <input id="roleSeller" name="role" type="radio" value="seller">
                            <span>
                                <strong>Продавець</strong>
                                <small>Отримає seller-акаунт, зможе працювати зі своїми товарами й переглядати статистику продажів.</small>
                            </span>
                        </label>
                    </div>
                </div>
                <div class="actions">
                    <button class="submit-btn" type="submit">Зареєструватися</button>
                    <button class="secondary-btn" type="button" data-switch-view="login">Повернутися до входу</button>
                </div>
            </form>
        </section>

        <p class="helper">Після успішного входу каталог на сайті автоматично синхронізується з базою даних. Для продавця додатково стане доступна статистика по товарах і замовленнях.</p>
    </section>
</body>
</html>`;
    }

    function createAccountPopupMarkup() {
        const userName = escapeHtml(state.user.Name || "Користувач");
        const email = escapeHtml(state.user.Email || "Email не вказано");
        const phone = escapeHtml(state.user.Phone || "Телефон не вказано");
        const country = escapeHtml(state.user.Country || "Країну не вказано");
        const cartCount = getCartCount();
        const accountType = getAccountTypeLabel();
        const sellerStatsMarkup = createSellerStatsMarkup();

        return `<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ваш акаунт TekLink</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 18px;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg, #f5f6f8 0%, #eaeef3 100%);
            color: #1d1d1f;
        }
        .account-card {
            width: 100%;
            max-width: 430px;
            background: #ffffff;
            border-radius: 18px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.14);
            border: 1px solid #d8dce2;
            padding: 24px;
        }
        h1 {
            margin: 0 0 8px;
            font-size: 28px;
        }
        .intro {
            margin: 0 0 18px;
            color: #5a6370;
            line-height: 1.5;
            font-size: 15px;
        }
        .profile {
            border: 1px solid #d6dde8;
            border-radius: 14px;
            padding: 16px;
            background: #f8fbff;
            display: grid;
            gap: 10px;
        }
        .profile strong {
            display: block;
            margin-bottom: 4px;
            font-size: 16px;
        }
        .profile span {
            display: block;
            color: #4a5768;
            line-height: 1.45;
            font-size: 14px;
        }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 18px;
        }
        .primary-btn,
        .secondary-btn {
            flex: 1;
            border: none;
            border-radius: 11px;
            padding: 12px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
        }
        .primary-btn {
            background: #0fa6ff;
            color: #ffffff;
        }
        .primary-btn:hover {
            background: #008fdc;
        }
        .secondary-btn {
            background: #eef2f6;
            color: #2e3d50;
        }
        .footer-note {
            margin-top: 14px;
            color: #43566f;
            font-size: 13px;
            line-height: 1.45;
        }
        .ghost-btn {
            border: 1px solid #cfd7e3;
            border-radius: 11px;
            background: #f4f7fb;
            color: #30445f;
            padding: 10px 12px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
        }
        .ghost-btn:disabled {
            cursor: wait;
            opacity: 0.7;
        }
        .seller-stats {
            margin-top: 18px;
            border: 1px solid #d6dde8;
            border-radius: 14px;
            padding: 16px;
            background: #fcfdff;
        }
        .seller-stats__header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 14px;
        }
        .seller-stats__header h2,
        .seller-stats__top h3 {
            margin: 0;
            font-size: 18px;
        }
        .seller-stats__grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 12px;
        }
        .seller-stats__card {
            border: 1px solid #e0e6ef;
            border-radius: 12px;
            padding: 12px;
            background: #f7fbff;
        }
        .seller-stats__card strong {
            display: block;
            margin-bottom: 4px;
            font-size: 18px;
        }
        .seller-stats__card span,
        .seller-stats__statuses span,
        .seller-stats__top li span {
            color: #4a5768;
            line-height: 1.45;
            font-size: 13px;
        }
        .seller-stats__statuses {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }
        .seller-stats__statuses span {
            border-radius: 999px;
            background: #eef5ff;
            padding: 6px 10px;
        }
        .seller-stats__top ul {
            margin: 10px 0 0;
            padding-left: 18px;
        }
        .seller-stats__top li {
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <section class="account-card">
        <h1>${state.sellerAnalytics ? "Кабінет продавця" : "Ваш акаунт"}</h1>
        <p class="intro">Ви вже авторизовані. Дані профілю й кошика синхронізовані з поточною сесією${state.sellerAnalytics ? ", а seller-статистика підтягнута з бекенду." : "."}</p>

        <div class="profile">
            <div>
                <strong>${userName}</strong>
                <span>Email: ${email}</span>
            </div>
            <div>
                <span>Телефон: ${phone}</span>
                <span>Країна: ${country}</span>
            </div>
            <div>
                <span>Тип акаунта: ${escapeHtml(accountType)}</span>
                <span>Товарів у кошику: ${cartCount}</span>
            </div>
        </div>

        ${sellerStatsMarkup}

        <div class="actions">
            <button class="primary-btn" type="button" id="goToCart">Перейти в кошик</button>
            <button class="secondary-btn" type="button" id="logoutBtn">Вийти</button>
        </div>

        <p class="footer-note">Після виходу товари в кошику залишаться локально, але для оформлення замовлення потрібно буде увійти знову. Якщо ви продавець, відкрийте це вікно ще раз у будь-який момент, щоб побачити актуальну статистику.</p>
    </section>
</body>
</html>`;
    }

    function switchPopupView(authWindow, viewName) {
        const panels = authWindow.document.querySelectorAll("[data-auth-view]");
        const buttons = authWindow.document.querySelectorAll("[data-auth-view-button]");

        panels.forEach(function (panel) {
            panel.hidden = panel.getAttribute("data-auth-view") !== viewName;
        });

        buttons.forEach(function (button) {
            button.classList.toggle("is-active", button.getAttribute("data-auth-view-button") === viewName);
        });
    }

    function attachGuestPopupHandlers(authWindow) {
        const statusBox = authWindow.document.getElementById("authStatus");
        const loginForm = authWindow.document.getElementById("loginForm");
        const registerForm = authWindow.document.getElementById("registerForm");

        function setStatus(message, tone) {
            if (!statusBox) {
                return;
            }

            statusBox.textContent = message || "";
            statusBox.setAttribute("data-tone", tone || "info");
        }

        function focusView(viewName) {
            switchPopupView(authWindow, viewName);
            if (viewName === "login") {
                const loginInput = authWindow.document.getElementById("loginName");
                if (loginInput) {
                    loginInput.focus();
                }
                return;
            }

            const registerInput = authWindow.document.getElementById("regName");
            if (registerInput) {
                registerInput.focus();
            }
        }

        authWindow.document.querySelectorAll("[data-auth-view-button]").forEach(function (button) {
            button.addEventListener("click", function () {
                focusView(button.getAttribute("data-auth-view-button"));
                setStatus("", "info");
            });
        });

        authWindow.document.querySelectorAll("[data-switch-view]").forEach(function (button) {
            button.addEventListener("click", function () {
                focusView(button.getAttribute("data-switch-view"));
                setStatus("", "info");
            });
        });

        if (loginForm) {
            loginForm.addEventListener("submit", async function (event) {
                event.preventDefault();

                const username = String(loginForm.elements.username.value || "").trim();
                const password = String(loginForm.elements.password.value || "");

                if (!username || !password) {
                    setStatus("Введіть ім'я користувача та пароль.", "error");
                    return;
                }

                setStatus("Виконую вхід і синхронізую каталог...", "info");

                try {
                    await loginUser(username, password);
                    setStatus("Успішно. Можна закривати вікно.", "success");
                    showToast("Вхід виконано успішно.", "success");
                    authWindow.close();
                } catch (error) {
                    setStatus(error.message, "error");
                }
            });
        }

        if (registerForm) {
            registerForm.addEventListener("submit", async function (event) {
                event.preventDefault();

                const payload = {
                    username: String(registerForm.elements.username.value || "").trim(),
                    email: String(registerForm.elements.email.value || "").trim(),
                    phone: String(registerForm.elements.phone.value || "").trim(),
                    country: String(registerForm.elements.country.value || "").trim(),
                    password: String(registerForm.elements.password.value || ""),
                    role: String(registerForm.elements.role.value || "user"),
                };

                if (!payload.username || !payload.email || !payload.password) {
                    setStatus("Заповніть ім'я, email і пароль.", "error");
                    return;
                }

                if (payload.password.length < 6) {
                    setStatus("Пароль має містити щонайменше 6 символів.", "error");
                    return;
                }

                setStatus("Створюю акаунт і одразу виконую вхід...", "info");

                try {
                    await registerUser(payload);
                    setStatus("Реєстрація завершена успішно.", "success");
                    showToast("Реєстрацію завершено успішно.", "success");
                    authWindow.close();
                } catch (error) {
                    setStatus(error.message, "error");
                }
            });
        }

        focusView("login");
    }

    function rerenderAuthWindow(authWindow) {
        authWindow.document.open();
        authWindow.document.write(createPopupMarkup());
        authWindow.document.close();
        attachPopupHandlers(authWindow);
    }

    function attachAccountPopupHandlers(authWindow) {
        const logoutButton = authWindow.document.getElementById("logoutBtn");
        const goToCartButton = authWindow.document.getElementById("goToCart");
        const refreshStatsButton = authWindow.document.getElementById("refreshStatsBtn");

        if (goToCartButton) {
            goToCartButton.addEventListener("click", function () {
                window.location.href = new URL("Сторінка кошика і оплати.html", window.location.href).toString();
                authWindow.close();
            });
        }

        if (refreshStatsButton) {
            refreshStatsButton.addEventListener("click", async function () {
                refreshStatsButton.disabled = true;
                refreshStatsButton.textContent = "Оновлюю...";
                await loadSellerAnalytics();
                rerenderAuthWindow(authWindow);
            });
        }

        if (logoutButton) {
            logoutButton.addEventListener("click", async function () {
                clearAuthState();
                await syncDynamicData({
                    silentCartSync: true,
                });
                showToast("Ви вийшли з акаунта.", "info");
                authWindow.close();
            });
        }
    }

    function attachPopupHandlers(authWindow) {
        if (state.user) {
            attachAccountPopupHandlers(authWindow);
            return;
        }

        attachGuestPopupHandlers(authWindow);
    }

    function openAuthWindow() {
        const authWindow = window.open("", popupName, popupFeatures);

        if (!authWindow) {
            window.alert("Браузер заблокував спливаюче вікно. Дозвольте pop-up для цього сайту.");
            return;
        }

        authWindow.document.open();
        authWindow.document.write(createPopupMarkup());
        authWindow.document.close();
        attachPopupHandlers(authWindow);
        authWindow.focus();
    }

    function updateAuthUi() {
        const authenticated = Boolean(state.user && isAuthenticated());
        const accountLabel = authenticated
            ? (state.sellerAnalytics ? "Кабінет продавця" : "Мій акаунт")
            : "Авторизація";
        const userName = authenticated ? String(state.user.Name || accountLabel) : accountLabel;

        document.querySelectorAll(triggerSelector).forEach(function (trigger) {
            trigger.classList.toggle("is-authenticated", authenticated);
            trigger.title = authenticated ? ("Увійшли як " + userName) : "Вхід або реєстрація";
            trigger.setAttribute("aria-label", authenticated ? ("Акаунт " + userName) : "Вхід або реєстрація");

            const label = trigger.querySelector("span");
            if (label) {
                label.textContent = accountLabel;
            }
        });
    }

    function updateCartBadges() {
        const cartCount = getCartCount();
        const cartLinks = document.querySelectorAll(
            ".top-icons a[href$='Сторінка кошика і оплати.html'], .mobile-menu__item[href$='Сторінка кошика і оплати.html']"
        );

        cartLinks.forEach(function (link) {
            let badge = link.querySelector(".cart-badge");
            if (!badge) {
                badge = document.createElement("span");
                badge.className = "cart-badge";
                link.appendChild(badge);
            }

            badge.textContent = String(cartCount);
            badge.hidden = cartCount === 0;
            link.classList.add("has-cart-badge");
            link.setAttribute("aria-label", cartCount > 0 ? ("Кошик, " + cartCount + " товарів") : "Кошик");
        });
    }

    function initAuthTriggers() {
        document.querySelectorAll(triggerSelector).forEach(function (trigger) {
            if (trigger.dataset.authBound === "true") {
                return;
            }

            trigger.dataset.authBound = "true";
            trigger.addEventListener("click", function (event) {
                event.preventDefault();
                openAuthWindow();
            });
        });
    }

    function ensureCatalogNotice() {
        const section = document.querySelector(".products");
        const grid = document.querySelector(".products-grid");

        if (!section || !grid) {
            return null;
        }

        let notice = section.querySelector(".product-sync-note");
        if (notice) {
            return notice;
        }

        notice = document.createElement("p");
        notice.className = "product-sync-note";
        section.insertBefore(notice, grid);
        return notice;
    }

    function setCatalogStatus(message, tone) {
        state.catalogStatus.message = message || "";
        state.catalogStatus.tone = tone || "info";
        renderCatalogNotice();
    }

    function renderCatalogNotice() {
        const notice = ensureCatalogNotice();
        if (!notice) {
            return;
        }

        const cards = Array.from(document.querySelectorAll(".products-grid .product-card"));
        const visibleCards = cards.filter(function (card) {
            return !card.hidden;
        }).length;

        let message = state.catalogStatus.message;
        let tone = state.catalogStatus.tone;

        if (state.currentSearch && cards.length > 0) {
            if (visibleCards === 0) {
                message = "За запитом \"" + state.currentSearch + "\" товарів не знайдено.";
                tone = "warning";
            } else {
                message = "Знайдено " + visibleCards + " товарів за запитом \"" + state.currentSearch + "\".";
                tone = "info";
            }
        }

        notice.textContent = message;
        notice.dataset.tone = tone;
        notice.hidden = !message;
    }

    function createSeededShuffle(total, seed) {
        const indices = Array.from({ length: total }, function (_, index) {
            return index;
        });
        let stateValue = seed >>> 0;

        function random() {
            stateValue = (stateValue * 1664525 + 1013904223) >>> 0;
            return stateValue / 4294967296;
        }

        for (let i = indices.length - 1; i > 0; i -= 1) {
            const j = Math.floor(random() * (i + 1));
            const temp = indices[i];
            indices[i] = indices[j];
            indices[j] = temp;
        }

        return indices;
    }

    function areSameOrder(first, second) {
        if (!first || !second || first.length !== second.length) {
            return false;
        }

        return first.every(function (value, index) {
            return value === second[index];
        });
    }

    function renderProductSlide(slideIndex, withAnimation) {
        const grid = document.querySelector(".products-grid");

        if (!grid || !state.slideCards.length || !state.slideOrders.length) {
            return;
        }

        if (withAnimation) {
            grid.classList.remove("products-grid--animating");
            void grid.offsetWidth;
            grid.classList.add("products-grid--animating");
        }

        const fragment = document.createDocumentFragment();
        state.slideOrders[slideIndex].forEach(function (cardIndex) {
            const card = state.slideCards[cardIndex];
            if (card) {
                fragment.appendChild(card);
            }
        });

        grid.appendChild(fragment);
        applyProductSearch(state.currentSearch);
    }

    function rebuildProductSlider() {
        const grid = document.querySelector(".products-grid");
        const prevButton = document.querySelector(".products-prev");
        const nextButton = document.querySelector(".products-more");

        if (!grid || !prevButton || !nextButton) {
            return;
        }

        const cards = Array.from(grid.querySelectorAll(".product-card"));
        state.slideCards = cards;
        state.currentSlideIndex = 0;

        if (!grid.dataset.sliderBound) {
            prevButton.addEventListener("click", function () {
                if (!state.slideOrders.length) {
                    return;
                }

                state.currentSlideIndex = (state.currentSlideIndex - 1 + state.slideOrders.length) % state.slideOrders.length;
                renderProductSlide(state.currentSlideIndex, true);
            });

            nextButton.addEventListener("click", function () {
                if (!state.slideOrders.length) {
                    return;
                }

                state.currentSlideIndex = (state.currentSlideIndex + 1) % state.slideOrders.length;
                renderProductSlide(state.currentSlideIndex, true);
            });

            grid.addEventListener("animationend", function () {
                grid.classList.remove("products-grid--animating");
            });

            grid.dataset.sliderBound = "true";
        }

        if (cards.length < 2) {
            state.slideOrders = [];
            prevButton.disabled = true;
            nextButton.disabled = true;
            return;
        }

        const baseOrder = cards.map(function (_, index) {
            return index;
        });
        const shuffledOrderOne = createSeededShuffle(cards.length, 20260422);
        const shuffledOrderTwo = createSeededShuffle(cards.length, 7772026);

        if (areSameOrder(baseOrder, shuffledOrderOne)) {
            shuffledOrderOne.reverse();
        }

        if (areSameOrder(baseOrder, shuffledOrderTwo) || areSameOrder(shuffledOrderOne, shuffledOrderTwo)) {
            shuffledOrderTwo.push(shuffledOrderTwo.shift());
        }

        state.slideOrders = [baseOrder, shuffledOrderOne, shuffledOrderTwo];
        prevButton.disabled = false;
        nextButton.disabled = false;
        renderProductSlide(0, false);
    }

    function applyProductSearch(rawQuery) {
        const grid = document.querySelector(".products-grid");
        if (!grid) {
            return;
        }

        state.currentSearch = normalizeText(rawQuery);

        Array.from(grid.querySelectorAll(".product-card")).forEach(function (card) {
            const searchText = normalizeText(card.dataset.searchText || card.textContent);
            card.hidden = Boolean(state.currentSearch) && !searchText.includes(state.currentSearch);
        });

        const prevButton = document.querySelector(".products-prev");
        const nextButton = document.querySelector(".products-more");
        const hasActiveSearch = Boolean(state.currentSearch);

        if (prevButton) {
            prevButton.style.display = hasActiveSearch ? "none" : "";
        }
        if (nextButton) {
            nextButton.style.display = hasActiveSearch ? "none" : "";
        }

        renderCatalogNotice();
    }

    function getSearchInput() {
        return document.querySelector(".search-wrap input[name='search']");
    }

    function getInitialSearchQuery() {
        return String(new URL(window.location.href).searchParams.get("search") || "").trim();
    }

    function updateSearchQueryInUrl(query) {
        const currentUrl = new URL(window.location.href);
        if (query) {
            currentUrl.searchParams.set("search", query);
        } else {
            currentUrl.searchParams.delete("search");
        }

        window.history.replaceState({}, "", currentUrl);
    }

    function createProductCardMarkup(product, index) {
        const title = escapeHtml(product.ProductName || "Товар");
        const image = escapeHtml(resolveProductImage(product.ProductName || "", product.ProductID || index));
        const stock = Number(product.AvailableQuantity) || 0;
        const disabled = stock <= 0;

        return `
            <article class="product-card" data-product-id="${product.ProductID}" data-search-text="${escapeHtml(normalizeText(product.ProductName || ""))}">
                <div class="product-card__image-wrap">
                    <img class="product-card__image" src="${image}" alt="${title}">
                </div>
                <h3 class="product-card__title">${title}</h3>
                <p class="product-card__meta">В наявності: ${stock}</p>
                <div class="product-card__bottom">
                    <p class="product-card__price">${formatPrice(product.Price)}</p>
                    <button class="product-card__cart-btn" type="button" data-add-to-cart="${product.ProductID}" ${disabled ? "disabled" : ""} aria-label="${disabled ? "Товар тимчасово недоступний" : "Додати товар у кошик"}">
                        <img class="product-card__cart" src="picture/Зелений кошик.png" alt="">
                    </button>
                </div>
            </article>
        `;
    }

    function prepareStaticProductCards() {
        const cards = document.querySelectorAll(".products-grid .product-card");
        cards.forEach(function (card) {
            const title = card.querySelector(".product-card__title");
            if (title) {
                card.dataset.searchText = normalizeText(title.textContent);
            }

            const staticCart = card.querySelector(".product-card__cart");
            if (staticCart) {
                staticCart.style.cursor = "pointer";
                staticCart.title = "Увійдіть, щоб додавати товари з бази у кошик";
            }
        });
    }

    async function loadProducts() {
        const products = await apiRequest("/product");
        return Array.isArray(products) ? products : [];
    }

    function renderLiveCatalog(products) {
        const grid = document.querySelector(".products-grid");
        if (!grid) {
            return;
        }

        if (!products.length) {
            grid.innerHTML = '<div class="products-empty">У базі даних поки немає товарів для відображення.</div>';
            state.slideCards = [];
            state.slideOrders = [];
            const prevButton = document.querySelector(".products-prev");
            const nextButton = document.querySelector(".products-more");
            if (prevButton) {
                prevButton.disabled = true;
            }
            if (nextButton) {
                nextButton.disabled = true;
            }
            applyProductSearch(state.currentSearch || getInitialSearchQuery());
            return;
        }

        grid.innerHTML = products.map(createProductCardMarkup).join("");
        rebuildProductSlider();
        applyProductSearch(getInitialSearchQuery());
    }

    async function syncProductCatalog() {
        const grid = document.querySelector(".products-grid");
        if (!grid) {
            return null;
        }

        prepareStaticProductCards();
        bindCatalogEvents();

        if (!isAuthenticated()) {
            state.products = [];
            rebuildProductSlider();
            applyProductSearch(getInitialSearchQuery());
            setCatalogStatus(
                "Увійдіть у свій акаунт, щоб каталог підтягувався безпосередньо з бази даних і товари можна було додавати у кошик.",
                "info"
            );
            return null;
        }

        try {
            const products = await loadProducts();
            state.products = products;
            renderLiveCatalog(products);
            setCatalogStatus(
                products.length
                    ? "Каталог синхронізовано з базою даних. Доступно " + products.length + " товарів."
                    : "Авторизація успішна, але в каталозі поки немає товарів у базі даних.",
                products.length ? "success" : "warning"
            );
            return products;
        } catch (error) {
            state.products = [];
            prepareStaticProductCards();
            rebuildProductSlider();
            applyProductSearch(getInitialSearchQuery());
            setCatalogStatus("Не вдалося завантажити каталог із бази даних: " + error.message, "error");
            return null;
        }
    }

    function addProductToCart(product) {
        if (!product) {
            return;
        }

        if (!isAuthenticated()) {
            showToast("Для додавання товарів у кошик потрібно увійти.", "info");
            openAuthWindow();
            return;
        }

        const availableQuantity = Number(product.AvailableQuantity) || 0;
        if (availableQuantity <= 0) {
            showToast("Цей товар зараз недоступний у базі даних.", "warning");
            return;
        }

        const cart = getCart();
        const existingItem = cart.find(function (item) {
            return item.productId === product.ProductID;
        });

        if (existingItem) {
            if (existingItem.quantity >= availableQuantity) {
                showToast("У кошику вже максимальна доступна кількість цього товару.", "warning");
                return;
            }

            existingItem.quantity += 1;
            existingItem.availableQuantity = availableQuantity;
            existingItem.price = roundMoney(product.Price);
        } else {
            cart.push({
                productId: product.ProductID,
                name: product.ProductName,
                price: roundMoney(product.Price),
                quantity: 1,
                image: resolveProductImage(product.ProductName || "", product.ProductID),
                availableQuantity: availableQuantity,
            });
        }

        setCart(cart);
        renderCartPage();
        showToast("Товар додано у кошик.", "success");
    }

    function bindCatalogEvents() {
        const grid = document.querySelector(".products-grid");
        if (!grid || grid.dataset.catalogBound === "true") {
            return;
        }

        grid.dataset.catalogBound = "true";
        grid.addEventListener("click", function (event) {
            const addButton = event.target.closest("[data-add-to-cart]");
            if (addButton) {
                const productId = Number(addButton.getAttribute("data-add-to-cart"));
                const product = state.products.find(function (item) {
                    return Number(item.ProductID) === productId;
                });
                addProductToCart(product);
                return;
            }

            const staticCartIcon = event.target.closest(".product-card__cart");
            if (staticCartIcon) {
                showToast("Увійдіть, щоб додавати товари з бази у кошик.", "info");
                openAuthWindow();
            }
        });
    }

    function initSearchForms() {
        document.querySelectorAll(".search-wrap").forEach(function (form) {
            if (form.dataset.searchBound === "true") {
                return;
            }

            form.dataset.searchBound = "true";
            const input = form.querySelector("input[name='search']");

            if (input && document.querySelector(".products-grid")) {
                input.value = getInitialSearchQuery();
                input.addEventListener("input", function () {
                    updateSearchQueryInUrl(input.value.trim());
                    applyProductSearch(input.value.trim());
                });
            }

            form.addEventListener("submit", function (event) {
                const query = input ? input.value.trim() : "";

                if (document.querySelector(".products-grid")) {
                    event.preventDefault();
                    updateSearchQueryInUrl(query);
                    applyProductSearch(query);
                    return;
                }

                if (!query) {
                    return;
                }

                event.preventDefault();
                const targetUrl = new URL("main.html", window.location.href);
                targetUrl.searchParams.set("search", query);
                window.location.href = targetUrl.toString();
            });
        });
    }

    function ensureShippingAddressField() {
        const form = document.querySelector(".form-grid");
        if (!form) {
            return null;
        }

        let field = form.querySelector("[name='shipping_address']");
        if (field) {
            return field;
        }

        field = document.createElement("input");
        field.type = "text";
        field.name = "shipping_address";
        field.placeholder = "Адреса доставки або номер відділення";

        const commentField = form.querySelector("textarea[name='comment']");
        if (commentField) {
            form.insertBefore(field, commentField);
        } else {
            form.appendChild(field);
        }

        return field;
    }

    function isOnlinePaymentMethod(paymentMethod) {
        return paymentMethod === "card" || paymentMethod === "parts";
    }

    function formatCardNumber(value) {
        return String(value || "")
            .replace(/\D/g, "")
            .slice(0, 16)
            .replace(/(\d{4})(?=\d)/g, "$1 ")
            .trim();
    }

    function formatCardExpiry(value) {
        const digits = String(value || "").replace(/\D/g, "").slice(0, 4);
        if (digits.length <= 2) {
            return digits;
        }
        return digits.slice(0, 2) + "/" + digits.slice(2);
    }

    function formatCardCvv(value) {
        return String(value || "").replace(/\D/g, "").slice(0, 3);
    }

    function ensureCardPaymentFields() {
        const form = document.querySelector(".form-grid");
        if (!form) {
            return null;
        }

        let container = form.querySelector(".payment-fields");
        if (container) {
            return container;
        }

        container = document.createElement("div");
        container.className = "payment-fields";
        container.hidden = true;
        container.innerHTML = `
            <div class="payment-fields__title">Дані картки для симуляції оплати</div>
            <p class="payment-fields__hint">Після підтвердження сайт покаже короткий стан "триває оплата", а потім оформить замовлення зі статусом Pending.</p>
            <div class="payment-fields__grid">
                <input type="text" name="card_number" inputmode="numeric" autocomplete="cc-number" placeholder="Номер картки" maxlength="19">
                <input type="text" name="card_holder" autocomplete="cc-name" placeholder="Ім'я власника картки">
                <input type="text" name="card_expiry" inputmode="numeric" autocomplete="cc-exp" placeholder="MM/YY" maxlength="5">
                <input type="text" name="card_cvv" inputmode="numeric" autocomplete="cc-csc" placeholder="CVV" maxlength="3">
            </div>
        `;

        const radioList = form.querySelector(".radio-list");
        if (radioList) {
            radioList.insertAdjacentElement("afterend", container);
        } else {
            form.appendChild(container);
        }

        return container;
    }

    function updatePaymentFieldsState() {
        const container = ensureCardPaymentFields();
        if (!container) {
            return;
        }

        const selectedPaymentField = document.querySelector(".form-grid [name='payment']:checked");
        const selectedPaymentMethod = selectedPaymentField ? String(selectedPaymentField.value || "") : "card";
        const shouldShowCardFields = isOnlinePaymentMethod(selectedPaymentMethod);
        container.hidden = !shouldShowCardFields;

        container.querySelectorAll("input").forEach(function (input) {
            input.required = shouldShowCardFields;
            input.disabled = !shouldShowCardFields;
        });
    }

    function validateCardPaymentFields(paymentMethod) {
        if (!isOnlinePaymentMethod(paymentMethod)) {
            return null;
        }

        const container = ensureCardPaymentFields();
        if (!container) {
            throw new Error("Не вдалося підготувати поля для оплати карткою.");
        }

        const cardNumberField = container.querySelector("[name='card_number']");
        const cardHolderField = container.querySelector("[name='card_holder']");
        const cardExpiryField = container.querySelector("[name='card_expiry']");
        const cardCvvField = container.querySelector("[name='card_cvv']");

        const cardNumber = formatCardNumber(cardNumberField ? cardNumberField.value : "");
        const cardHolder = String(cardHolderField ? cardHolderField.value : "").trim();
        const cardExpiry = formatCardExpiry(cardExpiryField ? cardExpiryField.value : "");
        const cardCvv = formatCardCvv(cardCvvField ? cardCvvField.value : "");

        if (cardNumberField) {
            cardNumberField.value = cardNumber;
        }
        if (cardExpiryField) {
            cardExpiryField.value = cardExpiry;
        }
        if (cardCvvField) {
            cardCvvField.value = cardCvv;
        }

        const cardDigits = cardNumber.replace(/\s/g, "");
        if (cardDigits.length !== 16) {
            throw new Error("Введіть коректний 16-значний номер картки.");
        }

        if (!cardHolder || cardHolder.length < 3) {
            throw new Error("Вкажіть ім'я власника картки.");
        }

        const expiryMatch = /^(\d{2})\/(\d{2})$/.exec(cardExpiry);
        if (!expiryMatch) {
            throw new Error("Вкажіть термін дії картки у форматі MM/YY.");
        }

        const expiryMonth = Number(expiryMatch[1]);
        if (!Number.isInteger(expiryMonth) || expiryMonth < 1 || expiryMonth > 12) {
            throw new Error("Місяць у терміні дії картки має бути від 01 до 12.");
        }

        if (cardCvv.length !== 3) {
            throw new Error("CVV має містити 3 цифри.");
        }

        return {
            cardNumber: cardDigits,
            cardHolder: cardHolder,
            cardExpiry: cardExpiry,
            cardCvv: cardCvv,
            last4: cardDigits.slice(-4),
        };
    }

    function ensureCheckoutFeedback() {
        const summary = document.querySelector(".summary");
        const checkoutButton = document.querySelector(".checkout-btn");

        if (!summary || !checkoutButton) {
            return null;
        }

        let feedback = summary.querySelector(".checkout-feedback");
        if (feedback) {
            return feedback;
        }

        feedback = document.createElement("div");
        feedback.className = "checkout-feedback";
        feedback.hidden = true;
        feedback.setAttribute("aria-live", "polite");
        summary.insertBefore(feedback, checkoutButton);
        return feedback;
    }

    function setCheckoutFeedback(message, tone, options) {
        const feedback = ensureCheckoutFeedback();
        if (!feedback) {
            return;
        }

        const settings = typeof options === "object" && options !== null
            ? options
            : {
                loading: Boolean(options),
            };

        feedback.hidden = !message;
        feedback.dataset.tone = tone || "info";
        feedback.classList.toggle("checkout-feedback--loading", Boolean(settings.loading));

        if (!message) {
            feedback.textContent = "";
            return;
        }

        if (settings.loading) {
            feedback.innerHTML = `
                <span class="checkout-spinner" aria-hidden="true"></span>
                <span>${escapeHtml(message)}</span>
            `;
            return;
        }

        feedback.textContent = message;
    }

    function prefillCheckoutForm() {
        const form = document.querySelector(".form-grid");
        if (!form || !state.user) {
            return;
        }

        ensureShippingAddressField();
        ensureCardPaymentFields();

        const fullNameInput = form.querySelector("[name='full_name']");
        const phoneInput = form.querySelector("[name='phone']");
        const emailInput = form.querySelector("[name='email']");

        if (fullNameInput && !fullNameInput.value) {
            fullNameInput.value = state.user.Name || "";
        }
        if (phoneInput && !phoneInput.value) {
            phoneInput.value = state.user.Phone || "";
        }
        if (emailInput && !emailInput.value) {
            emailInput.value = state.user.Email || "";
        }

        updatePaymentFieldsState();
    }

    function updateCartSummary() {
        const summaryLines = document.querySelectorAll(".summary .summary-line");
        if (summaryLines.length < 4) {
            return;
        }

        const cart = getCart();
        const itemsCount = cart.reduce(function (sum, item) {
            return sum + item.quantity;
        }, 0);

        const deliveryTypeField = document.querySelector(".form-grid [name='delivery_type']");
        const deliveryType = deliveryTypeField ? String(deliveryTypeField.value || "") : "";
        const delivery = deliveryOptions[deliveryType] || {
            price: 0,
            label: "",
        };

        const subtotal = getCartSubtotal(cart);
        const total = subtotal + delivery.price;

        summaryLines[0].children[0].textContent = "Товари (" + itemsCount + " шт.)";
        summaryLines[0].children[1].textContent = formatPrice(subtotal);
        summaryLines[1].children[0].textContent = "Знижка";
        summaryLines[1].children[1].textContent = formatPrice(0);
        summaryLines[2].children[0].textContent = "Доставка";
        summaryLines[2].children[1].textContent = formatPrice(delivery.price);
        summaryLines[3].children[0].textContent = "До сплати";
        summaryLines[3].children[1].textContent = formatPrice(total);

        const checkoutButton = document.querySelector(".checkout-btn");
        if (checkoutButton) {
            checkoutButton.disabled = cart.length === 0;
            checkoutButton.textContent = cart.length ? "Підтвердити замовлення" : "Кошик порожній";
        }

        const shippingAddressField = ensureShippingAddressField();
        if (shippingAddressField) {
            shippingAddressField.required = Boolean(deliveryType) && deliveryType !== "pickup";
            if (deliveryType === "pickup") {
                shippingAddressField.placeholder = "Для самовивозу адресу можна не вказувати";
            } else if (deliveryType === "courier") {
                shippingAddressField.placeholder = "Вкажіть точну адресу доставки";
            } else {
                shippingAddressField.placeholder = "Вкажіть адресу або номер відділення";
            }
        }

        updatePaymentFieldsState();
    }

    function renderCartPage() {
        const cartContainer = document.querySelector(".cart-items");
        if (!cartContainer) {
            return;
        }

        const deliverySection = cartContainer.querySelector(".page-block");
        if (!deliverySection) {
            return;
        }

        ensureShippingAddressField();

        cartContainer.querySelectorAll(".cart-item, .cart-empty").forEach(function (item) {
            item.remove();
        });

        const cart = getCart();
        if (!cart.length) {
            const emptyState = document.createElement("div");
            emptyState.className = "cart-empty";
            emptyState.innerHTML = `
                <h2>Кошик поки порожній</h2>
                <p>Додайте товари зі сторінки каталогу. Після входу сайт підтягне актуальні позиції з бази даних.</p>
            `;
            cartContainer.insertBefore(emptyState, deliverySection);
            updateCartSummary();
            return;
        }

        const fragment = document.createDocumentFragment();

        cart.forEach(function (item) {
            const article = document.createElement("article");
            article.className = "cart-item";
            article.dataset.productId = String(item.productId);

            const availabilityText = item.availableQuantity === null
                ? "Кількість у базі буде перевірена під час оформлення"
                : ("Доступно в базі: " + item.availableQuantity + " шт.");

            article.innerHTML = `
                <img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.name)}">
                <div class="cart-item__info">
                    <h2 class="cart-item__title">${escapeHtml(item.name)}</h2>
                    <p class="cart-item__meta">ID товару: ${item.productId} | ${escapeHtml(availabilityText)}</p>
                    <button class="cart-item__remove" type="button" data-cart-action="remove" data-product-id="${item.productId}">Видалити</button>
                </div>
                <div class="qty" aria-label="Кількість товару">
                    <button type="button" aria-label="Зменшити" data-cart-action="decrease" data-product-id="${item.productId}">-</button>
                    <span>${item.quantity}</span>
                    <button type="button" aria-label="Збільшити" data-cart-action="increase" data-product-id="${item.productId}">+</button>
                </div>
                <strong>${formatPrice(item.price * item.quantity)}</strong>
            `;

            fragment.appendChild(article);
        });

        cartContainer.insertBefore(fragment, deliverySection);
        updateCartSummary();
        prefillCheckoutForm();
        updatePaymentFieldsState();
    }

    function updateCartItemQuantity(productId, delta) {
        const cart = getCart().map(function (item) {
            if (item.productId !== productId) {
                return item;
            }

            const nextItem = Object.assign({}, item);
            const nextQuantity = nextItem.quantity + delta;
            const maxQuantity = Number.isFinite(Number(nextItem.availableQuantity)) && nextItem.availableQuantity !== null
                ? Number(nextItem.availableQuantity)
                : Number.MAX_SAFE_INTEGER;

            if (delta > 0 && nextItem.quantity >= maxQuantity) {
                showToast("У базі даних більше немає доступної кількості цього товару.", "warning");
                return nextItem;
            }

            nextItem.quantity = Math.max(1, nextQuantity);
            return nextItem;
        });

        setCart(cart);
        renderCartPage();
    }

    function removeCartItem(productId) {
        setCart(getCart().filter(function (item) {
            return item.productId !== productId;
        }));
        renderCartPage();
    }

    async function syncCartWithProducts(options) {
        const config = options || {};
        const silent = Boolean(config.silent);
        let products = Array.isArray(config.products) ? config.products : null;

        if (!products && isAuthenticated()) {
            try {
                products = await loadProducts();
            } catch (error) {
                if (!silent) {
                    showToast("Не вдалося синхронізувати кошик із базою даних: " + error.message, "warning");
                }
                renderCartPage();
                return null;
            }
        }

        if (!products) {
            renderCartPage();
            return null;
        }

        const productMap = new Map(
            products.map(function (product) {
                return [Number(product.ProductID), product];
            })
        );

        const currentCart = getCart();
        const syncedCart = [];

        currentCart.forEach(function (item, index) {
            const product = productMap.get(item.productId);
            if (!product) {
                return;
            }

            const availableQuantity = Number(product.AvailableQuantity) || 0;
            if (availableQuantity <= 0) {
                return;
            }

            syncedCart.push({
                productId: Number(product.ProductID),
                name: product.ProductName,
                price: roundMoney(product.Price),
                quantity: Math.min(item.quantity, availableQuantity),
                image: item.image || resolveProductImage(product.ProductName || "", index),
                availableQuantity: availableQuantity,
            });
        });

        const before = JSON.stringify(currentCart);
        const after = JSON.stringify(syncedCart);

        if (before !== after) {
            setCart(syncedCart);
            if (!silent) {
                showToast("Кошик синхронізовано з актуальними даними з бази.", "info");
            }
        }

        renderCartPage();
        return products;
    }

    async function handleCheckout() {
        const cart = getCart();
        if (!cart.length) {
            setCheckoutFeedback("Додайте товари у кошик перед оформленням замовлення.", "warning");
            return;
        }

        if (!isAuthenticated()) {
            setCheckoutFeedback("Для оформлення замовлення потрібно увійти в акаунт.", "warning");
            openAuthWindow();
            return;
        }

        const form = document.querySelector(".form-grid");
        if (!form) {
            setCheckoutFeedback("Не вдалося знайти форму оформлення.", "error");
            return;
        }

        const shippingAddressField = ensureShippingAddressField();
        const fullName = String(form.querySelector("[name='full_name']").value || "").trim();
        const phone = String(form.querySelector("[name='phone']").value || "").trim();
        const email = String(form.querySelector("[name='email']").value || "").trim();
        const deliveryType = String(form.querySelector("[name='delivery_type']").value || "").trim();
        const paymentMethod = String(form.querySelector("[name='payment']:checked") ? form.querySelector("[name='payment']:checked").value : "card");
        const shippingAddress = shippingAddressField ? String(shippingAddressField.value || "").trim() : "";
        const onlinePayment = isOnlinePaymentMethod(paymentMethod);

        if (!fullName || !phone || !deliveryType) {
            setCheckoutFeedback("Заповніть ПІБ, телефон і спосіб доставки.", "error");
            return;
        }

        if (deliveryType !== "pickup" && !shippingAddress) {
            setCheckoutFeedback("Вкажіть адресу доставки або номер відділення.", "error");
            return;
        }

        let cardPaymentDetails = null;
        try {
            cardPaymentDetails = validateCardPaymentFields(paymentMethod);
        } catch (error) {
            setCheckoutFeedback(error.message, "error");
            return;
        }

        const checkoutButton = document.querySelector(".checkout-btn");
        if (checkoutButton) {
            checkoutButton.disabled = true;
        }

        let createdOrderId = null;

        if (onlinePayment) {
            setCheckoutFeedback(
                "Дані картки прийнято. Статус замовлення: триває оплата...",
                "info",
                { loading: true }
            );
        } else {
            setCheckoutFeedback("Створюю замовлення й записую його в базу даних...", "info");
        }

        try {
            if (onlinePayment) {
                await delay(1700);
            }

            const products = await loadProducts();
            await syncCartWithProducts({
                silent: true,
                products: products,
            });

            const freshCart = getCart();
            if (!freshCart.length) {
                throw new Error("Кошик спорожнів після синхронізації. Додайте товари ще раз.");
            }

            const delivery = deliveryOptions[deliveryType] || deliveryOptions.pickup;
            const shippingValue = shippingAddress || "Самовивіз із магазину";

            const order = await apiRequest("/order", {
                method: "POST",
                body: {
                    OrderDate: new Date().toISOString(),
                    Status: "Pending",
                },
            });
            createdOrderId = order.OrderID;

            if (onlinePayment) {
                setCheckoutFeedback(
                    "Замовлення №" + createdOrderId + ": триває оплата, обробляю платіжні дані...",
                    "info",
                    { loading: true }
                );
                await delay(1600);
            }

            for (const item of freshCart) {
                await apiRequest("/orderdetail", {
                    method: "POST",
                    body: {
                        OrderID: createdOrderId,
                        ProductID: item.productId,
                        Quantity: item.quantity,
                        ShippingAddress: shippingValue,
                    },
                });
            }

            if (delivery.courierName && delivery.price > 0) {
                await apiRequest("/courier", {
                    method: "POST",
                    body: {
                        Name: delivery.courierName,
                        Country: "Ukraine",
                        Price: delivery.price,
                        OrderID: createdOrderId,
                    },
                });
            }

            const paymentStatus = onlinePayment ? "Paid" : "Pending";
            const totalAmount = roundMoney(getCartSubtotal(freshCart) + delivery.price);

            await apiRequest("/payment", {
                method: "POST",
                body: {
                    OrderID: createdOrderId,
                    Status: paymentStatus,
                    Amount: totalAmount,
                    PaymentDate: new Date().toISOString(),
                    PaymentMethod: paymentMethod,
                },
            });

            setCart([]);
            form.reset();
            prefillCheckoutForm();
            renderCartPage();

            if (onlinePayment) {
                setCheckoutFeedback(
                    "Замовлення №" + createdOrderId + " оплачено. Імітація платіжного шлюзу завершена, статус замовлення змінено на Pending. Картка •••• " + cardPaymentDetails.last4 + ".",
                    "success"
                );
                showToast("Оплату для замовлення №" + createdOrderId + " підтверджено.", "success");
            } else {
                setCheckoutFeedback(
                    "Замовлення №" + createdOrderId + " оформлено. Статус замовлення — Pending, оплата очікується при отриманні або підтвердженні.",
                    "success"
                );
                showToast("Замовлення №" + createdOrderId + " оформлено успішно.", "success");
            }

            if (document.querySelector(".products-grid")) {
                await syncProductCatalog();
            }
        } catch (error) {
            const message = createdOrderId
                ? "Замовлення №" + createdOrderId + " було створено, але завершити оформлення не вдалося: " + error.message
                : "Не вдалося оформити замовлення: " + error.message;
            setCheckoutFeedback(message, "error");
        } finally {
            if (checkoutButton) {
                checkoutButton.disabled = getCart().length === 0;
            }
        }
    }

    function initCartPage() {
        const cartContainer = document.querySelector(".cart-items");
        const form = document.querySelector(".form-grid");
        const checkoutButton = document.querySelector(".checkout-btn");

        if (!cartContainer) {
            return;
        }

        renderCartPage();

        if (cartContainer.dataset.cartBound !== "true") {
            cartContainer.dataset.cartBound = "true";
            cartContainer.addEventListener("click", function (event) {
                const actionButton = event.target.closest("[data-cart-action]");
                if (!actionButton) {
                    return;
                }

                const productId = Number(actionButton.getAttribute("data-product-id"));
                const action = actionButton.getAttribute("data-cart-action");

                if (action === "increase") {
                    updateCartItemQuantity(productId, 1);
                } else if (action === "decrease") {
                    updateCartItemQuantity(productId, -1);
                } else if (action === "remove") {
                    removeCartItem(productId);
                }
            });
        }

        if (form && form.dataset.summaryBound !== "true") {
            form.dataset.summaryBound = "true";
            ensureCardPaymentFields();
            form.addEventListener("change", function () {
                updateCartSummary();
                updatePaymentFieldsState();
                setCheckoutFeedback("", "info");
            });
            form.addEventListener("input", function (event) {
                if (event.target.name === "card_number") {
                    event.target.value = formatCardNumber(event.target.value);
                } else if (event.target.name === "card_expiry") {
                    event.target.value = formatCardExpiry(event.target.value);
                } else if (event.target.name === "card_cvv") {
                    event.target.value = formatCardCvv(event.target.value);
                }
            });
            ensureShippingAddressField();
            prefillCheckoutForm();
            updatePaymentFieldsState();
        }

        if (checkoutButton && checkoutButton.dataset.checkoutBound !== "true") {
            checkoutButton.dataset.checkoutBound = "true";
            checkoutButton.addEventListener("click", function () {
                handleCheckout();
            });
        }
    }

    async function syncDynamicData(options) {
        const config = options || {};

        if (document.querySelector(".products-grid")) {
            await syncProductCatalog();
        }

        if (document.querySelector(".cart-items")) {
            await syncCartWithProducts({
                silent: Boolean(config.silentCartSync),
            });
            prefillCheckoutForm();
        }
    }

    function initMobileBurgerMenu() {
        const burgerButton = document.querySelector(".burger-toggle");
        const mobileMenu = document.querySelector(".mobile-menu");

        if (!burgerButton || !mobileMenu) {
            return;
        }

        function closeMenu() {
            mobileMenu.classList.remove("mobile-menu--open");
            burgerButton.setAttribute("aria-expanded", "false");
        }

        burgerButton.addEventListener("click", function () {
            const isOpen = mobileMenu.classList.toggle("mobile-menu--open");
            burgerButton.setAttribute("aria-expanded", String(isOpen));
        });

        document.addEventListener("click", function (event) {
            if (!mobileMenu.contains(event.target) && !burgerButton.contains(event.target)) {
                closeMenu();
            }
        });

        mobileMenu.addEventListener("click", function (event) {
            if (event.target.closest("a")) {
                closeMenu();
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 768) {
                closeMenu();
            }
        });
    }

    async function initPageFeatures() {
        initAuthTriggers();
        initSearchForms();
        initMobileBurgerMenu();
        initCartPage();
        bindCatalogEvents();
        prepareStaticProductCards();
        rebuildProductSlider();
        updateAuthUi();
        updateCartBadges();
        applyProductSearch(getInitialSearchQuery());

        await loadCurrentUser();
        await syncDynamicData({
            silentCartSync: true,
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            initPageFeatures();
        });
    } else {
        initPageFeatures();
    }
})();

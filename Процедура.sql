DELIMITER //

CREATE PROCEDURE CreateRandomOrderForCustomer(
    IN p_name VARCHAR(100),
    IN p_address VARCHAR(255)
)
BEGIN
    DECLARE v_customer_id INT;
    DECLARE v_order_id INT;
    DECLARE v_total_amount DECIMAL(10,2);
    DECLARE v_email VARCHAR(100);
    DECLARE v_phone VARCHAR(20);
    DECLARE v_country VARCHAR(50);
    DECLARE v_courier_id INT;
    DECLARE v_courier_name VARCHAR(100);
    DECLARE v_courier_country VARCHAR(50);
    DECLARE v_courier_price DECIMAL(10,2);
    DECLARE v_product_limit INT;

    SET v_email = CONCAT(LOWER(REPLACE(p_name, ' ', '')), FLOOR(RAND()*1000), '@example.com');
    SET v_phone = CONCAT('+380', FLOOR(100000000 + RAND() * 899999999));
    SET v_country = 'Ukraine';

    SET FOREIGN_KEY_CHECKS = 0;

    INSERT INTO Customer (Name, Email, Phone, Country)
    VALUES (p_name, v_email, v_phone, v_country);
    SET v_customer_id = LAST_INSERT_ID();

    INSERT INTO Orders (OrderDate, CustomerID, ShippingAddress, Status)
    VALUES (NOW(), v_customer_id, p_address, 'Pending');
    SET v_order_id = LAST_INSERT_ID();

    SET v_product_limit = FLOOR(1 + RAND() * 3);

    INSERT INTO OrderDetail (OrderID, ProductID, Quantity)
    SELECT v_order_id, ProductID, FLOOR(1 + RAND() * 3)
    FROM Product
    ORDER BY RAND()
    LIMIT v_product_limit;

    SELECT CourierID, Name, Country, Price
    INTO v_courier_id, v_courier_name, v_courier_country, v_courier_price
    FROM Courier
    ORDER BY RAND()
    LIMIT 1;

    IF v_courier_id IS NULL THEN
        SET v_courier_name = CONCAT('Courier_', FLOOR(RAND()*1000));
        SET v_courier_country = 'Ukraine';
        SET v_courier_price = 10 + RAND() * 20;

        INSERT INTO Courier (Name, Country, Price, OrderID)
        VALUES (v_courier_name, v_courier_country, v_courier_price, v_order_id);
    ELSE
        INSERT INTO Courier (Name, Country, Price, OrderID)
        VALUES (v_courier_name, v_courier_country, v_courier_price, v_order_id);
    END IF;

    SELECT SUM(p.Price * od.Quantity)
    INTO v_total_amount
    FROM OrderDetail od
    JOIN Product p ON p.ProductID = od.ProductID
    WHERE od.OrderID = v_order_id;

    INSERT INTO Payment (OrderID, Status, Amount, PaymentDate)
    VALUES (v_order_id, 'Paid', v_total_amount, NOW());

    SET FOREIGN_KEY_CHECKS = 1;

    SELECT 
        c.Name AS Customer,
        c.Email,
        c.Phone,
        o.OrderID,
        o.OrderDate,
        p.ProductName,
        p.Price,
        od.Quantity,
        pay.Amount AS TotalAmount,
        cr.Name AS Courier
    FROM Orders o
    JOIN Customer c ON o.CustomerID = c.CustomerID
    JOIN OrderDetail od ON o.OrderID = od.OrderID
    JOIN Product p ON od.ProductID = p.ProductID
    JOIN Payment pay ON o.OrderID = pay.OrderID
    JOIN Courier cr ON o.OrderID = cr.OrderID
    WHERE o.OrderID = v_order_id;

END //

DELIMITER ;

CALL CreateRandomOrderForCustomer('Oleg Ohrin', '0867 st. Stepan Bandera 45');
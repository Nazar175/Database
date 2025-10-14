DELIMITER //

CREATE PROCEDURE CreateRandomOrderForCustomer(
    IN p_customer_id INT
)
BEGIN
    DECLARE v_order_id INT;
    DECLARE v_total_amount DECIMAL(10,2);
    DECLARE v_courier_name VARCHAR(100);
    DECLARE v_courier_country VARCHAR(50);
    DECLARE v_courier_price DECIMAL(10,2);
    DECLARE v_product_limit INT;
    DECLARE v_address VARCHAR(255);

    SELECT CONCAT('Street_', FLOOR(RAND()*100), ' ', Country)
    INTO v_address
    FROM Customer
    WHERE CustomerID = p_customer_id;

    INSERT INTO Orders (OrderDate, CustomerID, ShippingAddress, Status)
    VALUES (NOW(), p_customer_id, v_address, 'Pending');
    SET v_order_id = LAST_INSERT_ID();

    SET v_product_limit = FLOOR(1 + RAND() * 3);

    INSERT INTO OrderDetail (OrderID, ProductID, Quantity)
    SELECT v_order_id, ProductID, FLOOR(1 + RAND() * 3)
    FROM Product
    ORDER BY RAND()
    LIMIT v_product_limit;

    SET v_courier_name = CONCAT('Courier_', FLOOR(RAND()*1000));
    SET v_courier_country = 'Ukraine';
    SET v_courier_price = 10 + RAND() * 20;

    INSERT INTO Courier (Name, Country, Price, OrderID)
    VALUES (v_courier_name, v_courier_country, v_courier_price, v_order_id);

    SELECT SUM(p.Price * od.Quantity)
    INTO v_total_amount
    FROM OrderDetail od
    JOIN Product p ON p.ProductID = od.ProductID
    WHERE od.OrderID = v_order_id;

    INSERT INTO Payment (OrderID, Status, Amount, PaymentDate)
    VALUES (v_order_id, 'Paid', v_total_amount, NOW());

    SELECT 
        c.Name AS Customer,
        c.Email,
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

CALL CreateRandomOrderForCustomer(3);
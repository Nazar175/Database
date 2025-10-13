WITH ProductOrders AS (
    SELECT 
        od.ProductID,
        od.OrderID,
        o.CustomerID,
        SUM(od.Quantity) AS TotalQuantity
    FROM OrderDetail od
    JOIN Orders o ON od.OrderID = o.OrderID
    GROUP BY od.ProductID, od.OrderID, o.CustomerID
)
SELECT 
    p.ProductName AS Product,
    COUNT(DISTINCT po.OrderID) AS TotalOrders,
    COUNT(DISTINCT po.CustomerID) AS TotalCustomers,
    SUM(po.TotalQuantity * p.Price) AS TotalSales
FROM Product p
JOIN ProductOrders po ON p.ProductID = po.ProductID
GROUP BY p.ProductID, p.ProductName
ORDER BY TotalSales DESC;
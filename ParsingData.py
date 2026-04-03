class AddrData:
    def __init__(self, data: list):
        try:
            self._all_data = {"КодРегион": 77,
                          "Индекс": data[1],
                          "Город": data[2],
                          "Район": data[3],
                          "НаселПункт": data[4],
                          "НетЗнач": data[5],
                          "Улица": data[6],
                          "Дом": data[7],
                          "Корпус": data[8],
                          "Кварт": data[9]}
        except:
            msg = f"Некорректно задан адреc:{data}"
            print(msg)
            raise Exception(msg)

    def get_data(self):
        return {k: v for k, v in self._all_data.items() if v}

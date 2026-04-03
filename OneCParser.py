import datetime
import json

from bs4 import BeautifulSoup

from ParsingData import AddrData
from UpdGenerator import Product

DOC_INFO_FILE_NAME = "static_data/DocumentInfo.json"
OKEI_FILE_NAME = "static_data/okei.xml"


class OneCParser:
    def __init__(self, data, doc_type):
        self._data = BeautifulSoup(data, features="xml")
        self.doc_type = doc_type

    def get_data(self):
        return {"Документ": self.prepare_document_info(),
                "СчФакт": self.prepare_invoice_data(),
                "ТаблСчФакт": self.prepare_product_table_data(),
                "СвПродПер": self.get_compl_operation_info()}

    def prepare_document_info(self):
        with open(DOC_INFO_FILE_NAME, 'r', encoding="utf-8") as file:
            try:
                static_file_data = json.loads(file.read())[self.doc_type]
            except:
                print(f"Неверный тип документа! {self.doc_type}")
        dynamic_data = {"ВремИнфПр": datetime.datetime.now().strftime("%H.%M.%S"),
                        "ДатаИнфПр": datetime.datetime.now().strftime("%d.%m.%Y"),
                        "НаимЭконСубСост": self.get_seller_full_naming()}

        return dynamic_data | static_file_data

    def get_seller_full_naming(self) -> str:
        seller = self._data.find("Контрагент")
        seller_name = seller["ОтображаемоеНаименование"]
        seller_inn = "ИНН "
        seller_kpp = "КПП "
        if "ИНН" in seller:
            seller_inn = "ИНН " + seller["ИНН"]
        if "КПП" in seller:
            seller_kpp = "КПП " + seller["КПП"]
        return ' '.join(["Общество с ограниченной ответственностью", seller_name, seller_inn, seller_kpp])

    def get_compl_operation_info(self) -> dict:
        doc = self._data.find("Документ")
        invoice_n_parsed = doc["Номер"].replace("М", "").lstrip("0")
        return {"НаимОсн": "Без документа-основания",
                "СодОпер": "Товары переданы"}

    def prepare_invoice_data(self):
        doc = self._data.find("Документ")
        date_arr = doc["Дата"].split("-")
        date_str = '.'.join(list(reversed(date_arr)))
        invoice_n_parsed = doc["Номер"].replace("М", "").lstrip("0")
        invoice_data = {"ДатаСчФ": date_str,
                        "НомерСчФ": invoice_n_parsed,
                        "КодОКВ": "643"}

        doc = self._data.findAll("Контрагент")

        if len(doc) < 2:
            raise Exception("В файле из 1С нет 2ух Контрагентов")

        seller = {"НаимОрг": doc[0]["Наименование"],
                  "ФактическийАдрес": AddrData(doc[0]["Адрес"].split(",")).get_data(),
                  "ЮридическийАдрес": AddrData(doc[0]["ЮридическийАдрес"].split(",")).get_data()
                  # ,"ИНН": doc[0]["ИННЮЛ"]
                  # ,"КПП": doc[0]["КПП"]
            , "ИНН": ""
            , "КПП": ""
                  }

        buyer = {"НаимОрг": doc[1]["Наименование"],
                 "ФактическийАдрес": AddrData(doc[1]["Адрес"].split(",")).get_data(),
                 "ЮридическийАдрес": AddrData(doc[1]["ЮридическийАдрес"].split(",")).get_data()
                 # ,"ИНН": doc[1]["ИННЮЛ"]
                 # ,"КПП": doc[1]["КПП"]
            , "ИНН": ""
            , "КПП": ""
                 }

        retval = {
            "СчетФ": invoice_data,
            "Продавец": seller,
            "Покупатель": buyer,
            "ДопСвФХЖ1": {"НаимОКВ": "Российский рубль"}
        }
        return retval

    def generate_table_tag(self, products):
        soup = BeautifulSoup(features="xml")
        table_tag = soup.new_tag(name="ТаблСчФакт")
        total_no_vat = 0
        total_sum = 0
        total_tax = 0
        count = 0
        for elem in products:
            count += 1
            table_tag.append(elem.prepare_new_tag(count))
            total_no_vat += elem.sum
            total_sum += elem.total_sum
            total_tax += elem.tax_sum

        total_tag = soup.new_tag(name="ВсегоОпл")
        total_tag.attrs = {
            "СтТовБезНДСВсего": f"{total_no_vat:.2f}",
            "СтТовУчНалВсего": f"{total_sum:.2f}"
        }
        total_tag_vat_sum = soup.new_tag(name="СумНал")
        total_tag_vat_sum.string = f"{total_tax:.2f}"
        total_tag_inside_vat = soup.new_tag(name="СумНалВсего")
        total_tag_inside_vat.append(total_tag_vat_sum)
        total_tag.append(total_tag_inside_vat)
        table_tag.append(total_tag)
        return table_tag

    def prepare_product_table_data(self):
        with open(OKEI_FILE_NAME, 'r', encoding="utf-8") as f:
            unit_codes = {}
            for tag in BeautifulSoup(f.read(), features="xml").find_all("elem"):
                unit_codes[tag["name"]] = tag["code"]

        catalog = self._data.find("Каталог")
        product_tags = catalog.find_all("Товар")
        product_names = {}
        for elem in product_tags:
            product_names[elem["ИдентификаторВКаталоге"]] = elem["Наименование"]

        products = []
        for tag in self._data.findAll("ТоварнаяПозиция"):
            name = product_names[tag["Товар"]]
            unit_code = unit_codes[tag["Единица"]]
            products.append(Product(tag, name, unit_code).prepare_json_data())

        return products

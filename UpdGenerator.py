import os.path
import uuid
from copy import copy

from bs4 import BeautifulSoup, NavigableString

RESULT_FOLDER_NAME = "result"


class ProductTable:
    def __init__(self, data):
        self.main_tag = "ТаблСчФакт"
        self.table_data = data
        self.soup = BeautifulSoup(features="xml")

    def makeTag(self):
        table_tag = self.soup.new_tag(name=self.main_tag)
        total_no_vat = 0
        total_sum = 0
        total_tax = 0
        count = 0
        for elem in self.table_data:
            count += 1
            table_tag.append(self.makeProductTag(elem, count))
            total_no_vat += elem["sums"]["sum"]
            total_sum += elem["sums"]["total_sum"]
            if elem["taxes"]:
                total_tax += elem["sums"]["tax_sum"]

        total_tag = self.soup.new_tag(name="ВсегоОпл")
        total_tag.attrs = {
            "СтТовБезНДСВсего": f"{total_no_vat:.2f}",
            "СтТовУчНалВсего": f"{total_sum:.2f}"
        }
        total_tag_vat_sum = self.soup.new_tag(name="СумНал")
        total_tag_vat_sum.string = f"{total_tax:.2f}"
        total_tag_inside_vat = self.soup.new_tag(name="СумНалВсего")
        total_tag_inside_vat.append(total_tag_vat_sum)
        total_tag.append(total_tag_inside_vat)
        table_tag.append(total_tag)
        return table_tag

    def makeProductTag(self, product, count):
        product["СведТов"]["НомСтр"] = str(count)
        main_tag = self.soup.new_tag(name="СведТов", attrs=product["СведТов"])

        excise_tag = self.soup.new_tag(name="Акциз")
        for key, value in product["Акциз"].items():
            excise_inside_tag = self.soup.new_tag(name=key)
            excise_inside_tag.insert(0, NavigableString(value))
            excise_tag.append(excise_inside_tag)
            main_tag.append(excise_tag)

        tax_sum_tag = self.soup.new_tag(name="СумНал")
        tax_sum_data = product["СумНал"]["СумНал"]
        tax_sum_tag_inside = copy(tax_sum_tag)
        tax_sum_tag_inside.string = str(tax_sum_data)
        tax_sum_tag.append(tax_sum_tag_inside)
        main_tag.append(tax_sum_tag)

        additional_information_tag = self.soup.new_tag(name="ДопСведТов")
        additional_information_data = product["ДопСведТов"]
        additional_information_tag["НаимЕдИзм"] = additional_information_data["НаимЕдИзм"]
        additional_information_tag["КодТов"] = additional_information_data["КодТов"]
        main_tag.append(additional_information_tag)

        return main_tag


class UpdGenerator:
    def __init__(self, json_data, file_name):
        self.file_name = os.path.basename(file_name)
        self.json_data = json_data
        self.soup = BeautifulSoup(features="xml")

    def generate_doc(self):
        main_file_tag = FileInfo("snd_upd_gen 1.0", "5.01").makeTag()
        edo_tag = ParticipantsEDOInfo(self.json_data["ЭДО"]).makeTag()
        doc_tag = DocumentInfo(self.json_data["Документ"]).makeTag()
        table_tag = ProductTable(self.json_data["ТаблСчФакт"]).makeTag()
        invoice_tag = InvoiceDetails(self.json_data["СчФакт"]).makeTag()
        completed_operation_tag = CompletedOperationInfo(self.json_data["СвПродПер"]).makeTag()
        signatory_tag = Signatory(self.json_data["Подписант"]).makeTag()

        main_file_tag.append(edo_tag)
        doc_tag.append(invoice_tag)
        doc_tag.append(table_tag)
        doc_tag.append(completed_operation_tag)
        doc_tag.append(signatory_tag)
        main_file_tag.append(doc_tag)

        self.soup.append(main_file_tag)
        with open(os.path.join(os.path.curdir, RESULT_FOLDER_NAME, self.file_name), 'w', encoding="utf-8") as fd:
            fd.write(str(self.soup))


class FileInfo:
    def __init__(self, prog_name, form_ver):
        self.main_tag = "Файл"
        self.main_tag_attrs = {"ИдФайл": uuid.uuid4(),
                               "ВерсПрог": prog_name,
                               "ВерсФорм": form_ver}

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        return soup.new_tag(name=self.main_tag, attrs=self.main_tag_attrs)


class ParticipantsEDOInfo:
    def __init__(self, data):
        self.main_tag = "СвУчДокОбор"
        self.main_tag_attr = {"ИдОтпр": data["ИдОтпр"],
                              "ИдПол": data["ИдПол"]}
        self.SellerEDOInfo = self.SellerEDOInfo(data)

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
        tag.append(self.SellerEDOInfo.makeTag())
        return tag

    class SellerEDOInfo:
        def __init__(self, data):
            self.main_tag = "СвОЭДОтпр"
            self.main_tag_attr = {"ИННЮЛ": data["ИННЮЛ"],
                                  "ИдЭДО": data["ИдЭДО"],
                                  "НаимОрг": data["НаимОрг"]}

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            return soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)


class DocumentInfo:
    def __init__(self, data):
        self.main_tag = "Документ"
        self.main_tag_attr = {"КНД": data["КНД"],
                              "Функция": data["Функция"],
                              "ПоФактХЖ": data["ПоФактХЖ"],
                              "НаимЭконСубСост": data["НаимЭконСубСост"],
                              "НаимДокОпр": data["НаимДокОпр"],
                              "ДатаИнфПр": data["ДатаИнфПр"],
                              "ВремИнфПр": data["ВремИнфПр"]}

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        return soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)


class InvoiceDetails:
    def __init__(self, data):
        self.main_tag = "СвСчФакт"
        self.main_tag_attr = {"ДатаСчФ": data["СчетФ"]["ДатаСчФ"],
                              "КодОКВ": data["СчетФ"]["КодОКВ"],
                              "НомерСчФ": data["СчетФ"]["НомерСчФ"]}

        self.seller_details = self.SellerBuyerDetails("СвПрод", data["Продавец"])
        self.buyer_details = self.SellerBuyerDetails("СвПокуп", data["Покупатель"])
        self.sender_details = self.CargoSenderReceiver(data["Продавец"], "ГрузОт", "ГрузОтпр")
        self.receiver_details = self.CargoSenderReceiver(data["Покупатель"], "ГрузПолуч")
        self.additional_info = self.AdditionalInfo(data["ДопСвФХЖ1"])

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
        tag.append(self.seller_details.makeTag())
        tag.append(self.sender_details.makeTag())
        tag.append(self.receiver_details.makeTag())
        tag.append(self.buyer_details.makeTag())
        tag.append(self.additional_info.makeTag())
        return tag

    class SellerBuyerDetails:
        def __init__(self, tag_name, data):
            self.tagName = tag_name
            self.id_info = IdentificationInformation(data)
            self.addr = Addr(data["ЮридическийАдрес"])

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            tag = soup.new_tag(name=self.tagName)
            tag.append(self.id_info.makeTag())
            tag.append(self.addr.makeTag())
            return tag

    class CargoSenderReceiver:
        def __init__(self, data, main_tag_name, inside_tag_name=""):
            self.main_tag_name: str = main_tag_name
            self.secondary_tag_name: str = inside_tag_name
            self.id_info = IdentificationInformation(data)
            self.addr = Addr(data["ФактическийАдрес"])

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            main_tag = soup.new_tag(name=self.main_tag_name)
            if not self.secondary_tag_name:
                main_tag.append(self.id_info.makeTag())
                main_tag.append(self.addr.makeTag())
            else:
                inside_tag = soup.new_tag(name=self.secondary_tag_name)
                inside_tag.append(self.id_info.makeTag())
                inside_tag.append(self.addr.makeTag())
                main_tag.append(inside_tag)
            return main_tag

    class AdditionalInfo:
        def __init__(self, data):
            self.main_tag = "ДопСвФХЖ1"
            self.main_tag_attr = {"НаимОКВ": data["НаимОКВ"]}

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
            return tag


class IdentificationInformation:
    def __init__(self, data):
        self.tagName = "ИдСв"
        if "ИП" in data["НаимОрг"]:
            self.entity_info = IPEntityInfo(data)
        else:
            self.entity_info = LegalEntityInfo(data)

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        tag = soup.new_tag(name=self.tagName)
        tag.append(self.entity_info.makeTag())
        return tag


class LegalEntityInfo:
    def __init__(self, data):
        self.main_tag = "СвЮЛУч"
        self.main_tag_attr = {"ИННЮЛ": data["ИНН"],
                              "КПП": data["КПП"],
                              "НаимОрг": data["НаимОрг"]}

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        return soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)


class IPEntityInfo:
    def __init__(self, data):
        self.main_tag = "СвИП"
        self.main_tag_attr = {"ИННФЛ": data["ИНН"]}
        self.FIO = self.FIO(data)

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
        tag.append(self.FIO.makeTag())
        return tag

    class FIO:
        def __init__(self, data):
            try:
                self.main_tag = "ФИО"
                fio = data["НаимОрг"].split(" ")
                self.main_tag_attr = {"Фамилия": fio[1],
                                      "Имя": fio[2],
                                      "Отчество": fio[3]}
            except:
                msg = f"Некорректный атрибут ФИО для ИП"
                print(msg)
                raise Exception(msg)

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
            return tag


class Addr:
    def __init__(self, data):
        self.tagName = "Адрес"
        self.AddrRF = self.AddrRF(data)

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        tag = soup.new_tag(name=self.tagName)
        tag.append(self.AddrRF.makeTag())
        return tag

    class AddrRF:
        def __init__(self, data):
            self.main_tag = "АдрРФ"
            self.main_tag_attr = data

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
            return tag


class CompletedOperationInfo:
    def __init__(self, data):
        self.main_tag = "СвПродПер"
        self.broadcast_info = self.BroadcastInfo(data)

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        main_tag = soup.new_tag(name=self.main_tag)
        main_tag.append(self.broadcast_info.makeTag())
        return main_tag

    class BroadcastInfo:
        def __init__(self, data):
            self.main_tag = "СвПер"
            self.main_tag_attr = {"СодОпер": data["СодОпер"]}
            self.transfer_basis_main_tag = "ОснПер"
            self.transfer_basis_inside_tag = "ОснПер"
            self.transfer_basis_inside_tag_data = {"НаимОсн": data["НаимОсн"]}

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            main_tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_attr)
            transfer_basis_main_tag = soup.new_tag(name=self.transfer_basis_inside_tag,
                                                   attrs=self.transfer_basis_inside_tag_data)
            main_tag.append(transfer_basis_main_tag)
            return main_tag


class Signatory:
    def __init__(self, data):
        self.main_tag = "Подписант"
        self.main_tag_args = {"ОблПолн": data["ОблПолн"],
                              "ОснПолн": data["ОснПолн"],
                              "Статус": data["Статус"]}
        self.legal_entity = self.LegalEntity(data)

    def makeTag(self):
        soup = BeautifulSoup(features="xml")
        main_tag = soup.new_tag(name=self.main_tag, attrs=self.main_tag_args)
        main_tag.append(self.legal_entity.makeTag())
        return main_tag

    class LegalEntity:
        def __init__(self, data):
            self.tagName = "ЮЛ"
            self.main_tag_attr = {"Должн": data["ЮЛ"]["Должн"],
                                  "ИННЮЛ": data["ЮЛ"]["ИННЮЛ"],
                                  "НаимОрг": data["ЮЛ"]["НаимОрг"],
                                  }
            self.full_name = self.FullName(data["ФИО"])

        def makeTag(self):
            soup = BeautifulSoup(features="xml")
            tag = soup.new_tag(name=self.tagName, attrs=self.main_tag_attr)
            tag.append(self.full_name.makeTag())
            return tag

        class FullName:
            def __init__(self, data):
                self.tagName = "ФИО"
                self.main_tag_attr = {"Имя": data["Имя"],
                                      "Фамилия": data["Фамилия"],
                                      "Отчество": data["Отчество"]}

            def makeTag(self):
                soup = BeautifulSoup(features="xml")
                tag = soup.new_tag(name=self.tagName, attrs=self.main_tag_attr)
                return tag


class Product:
    def __init__(self, main_tag, product_name, unit_code):
        self.product_name = product_name
        self.product_id = main_tag["Товар"].lstrip('0')
        self.unit = main_tag["Единица"]
        self.unit_code = unit_code
        self.qty = main_tag["Количество"]
        self.cost = main_tag["Цена"]
        self.sum = float(main_tag["Сумма"])

        self.tax_tag = main_tag.findNext("СуммаНалога")
        if self.tax_tag:
            self.tax_percent = self.tax_tag["Ставка"] + "%"
            self.tax_sum = float(self.tax_tag["Сумма"])
            if self.tax_tag.has_attr("ВключенВСумму"):
                self.total_sum = float(self.sum)
            else:
                self.total_sum = float(self.sum) + float(self.tax_sum)

        else:
            self.tax_percent = "без НДС"
            self.tax_sum = "без НДС"
            self.total_sum = float(self.sum)

    def prepare_json_data(self):
        data = {"СведТов": {"НомСтр": "",
                            "НаимТов": self.product_name,
                            "ОКЕИ_Тов": self.unit_code,
                            "КолТов": self.qty,
                            "ЦенаТов": self.cost,
                            "СтТовБезНДС": f"{self.sum:.2f}",
                            "НалСт": self.tax_percent,
                            "СтТовУчНал": f"{self.total_sum:.2f}",
                            },
                "СумНал": {"СумНал": self.tax_sum},
                "Акциз": {"БезАкциз": "без акциза"},
                "ДопСведТов": {"НаимЕдИзм": self.unit,
                               "КодТов": self.product_id},
                "taxes": 1 if self.tax_tag else 0,
                "sums": {"sum": self.sum,
                         "total_sum": self.total_sum,
                         "tax_sum": self.tax_sum}
                }
        return data

    def prepare_new_tag(self, string_num):
        soup = BeautifulSoup(features="xml")
        main_tag = soup.new_tag(name="СведТов")
        main_tag.attrs = {
            "НомСтр": str(string_num),
            "НаимТов": self.product_name,
            "ОКЕИ_Тов": self.unit_code,
            "КолТов": self.qty,
            "ЦенаТов": self.cost,
            "СтТовБезНДС": f"{self.sum:.2f}",
            "НалСт": self.tax_percent,
            "СтТовУчНал": f"{self.total_sum:.2f}"
        }

        excise_tag = soup.new_tag(name="Акциз")
        excise_inside_tag = soup.new_tag(name="БезАкциз")
        excise_inside_tag.insert(0, NavigableString("без акциза"))
        excise_tag.append(excise_inside_tag)
        main_tag.append(excise_tag)

        tax_sum_tag = soup.new_tag(name="СумНал")
        tax_sum_tag_inside = copy(tax_sum_tag)
        tax_sum_tag_inside.string = str(self.tax_sum)
        tax_sum_tag.append(tax_sum_tag_inside)
        main_tag.append(tax_sum_tag)

        additional_information_tag = soup.new_tag(name="ДопСведТов")
        additional_information_tag["НаимЕдИзм"] = self.unit
        additional_information_tag["КодТов"] = self.product_id
        main_tag.append(additional_information_tag)

        soup.append(main_tag)
        return soup.find("СведТов")

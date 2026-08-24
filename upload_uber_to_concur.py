import json
import os
import requests
import glob
import time
import pymupdf

from utils import get_license_uber, get_fare_amount_uber, get_date_uber

PDF_FOLDER = "workspace/uber_receipts"

DELAY_SECONDS = 0.5


# ==========================
# Configuration
# ==========================
REPORT_ID = "D1F96CE50FA142BDB110"
USER_ID = "d8140dfb-cd2d-40a2-acdf-a1dc21366b8e"

COOKIE_FILE = "Concur_Cookie.txt"

BUSINESS_PURPOSE = "Commute"
VENDOR_NAME = "Uber"

UPLOAD_URL = "https://www-us2.api.concursolutions.com/spend-graphql/upload"
GRAPHQL_URL = "https://www-us2.api.concursolutions.com/spend-graphql/graphql"

GRAPHQL_MUTATION = """
mutation SaveNewExpenseEntry($reportId: ID!, $contextRole: ContextRoleType!, $userId: ID!, $fields: CreateExpenseFieldsInput!, $taxFields: [TaxField!] = null, $expenseTypeId: String!, $policyId: String!, $shouldIncludeRpeKey: Boolean = false, $expenseListDetailFormId: String, $isTrexEnabled: Boolean!) {
  createExpense(
    dataContext: {reportId: $reportId, fields: $fields, taxFields: $taxFields, expenseListDetailFormId: $expenseListDetailFormId}
    userContext: {userId: $userId, contextType: $contextRole}
  ) {
    id
    rpeKey @include(if: $shouldIncludeRpeKey)
    reportDetails @include(if: $isTrexEnabled) {
      ...ExpenseReportDetailsFragment
      __typename
    }
    entry @include(if: $isTrexEnabled) {
      ...EreExpenseEntrySummaryFragment
      __typename
    }
    existingExpenseForm @include(if: $isTrexEnabled) {
      ...ExistingExpenseFormFragment
      __typename
    }
    entryExceptions @include(if: $isTrexEnabled) {
      ...EreEntryExceptionsFragment
      __typename
    }
    expenseTypeFilters @include(if: $isTrexEnabled) {
      shouldFilterCashAdvanceExpenseTypes
      shouldFilterCompanyCarExpenseType
      shouldFilterPersonalCarExpenseType
      __typename
    }
    vehicleRegistrationInfo @include(if: $isTrexEnabled) {
      hasPersonalCar
      hasCompanyCar
      __typename
    }
    __typename
  }
  CDS_addRecentExpenseTypes(policyId: $policyId, expenseTypeId: $expenseTypeId)
}

fragment EreEntryExceptionsFragment on EntryExceptions {
  reportId
  expenseId
  attendeesExceptionLevel
  transactionAmount {
    value
    currencyCode
    __typename
  }
  transactionDate
  expenseType {
    id
    code
    name
    meta {
      isJapanPublicTransportation
      __typename
    }
    __typename
  }
  countOfExceptions
  hasBlockingExceptions
  entryExceptions {
    allocationId
    exceptionCode
    expenseId
    isBlocking
    message
    parameters {
      entryExceptionAttendees {
        lastName
        firstName
        entryAmount
        crnCode
        totalExpensed
        totalAuthorized
        __typename
      }
      missingFields {
        missingSpecialParentField
        fields
        fieldIds
        __typename
      }
      __typename
    }
    parentExpenseId
    __typename
  }
  itemizationsExceptions {
    reportId
    expenseId
    attendeesExceptionLevel
    itemizationId
    transactionAmount {
      value
      currencyCode
      __typename
    }
    transactionDate
    expenseType {
      id
      code
      name
      meta {
        isJapanPublicTransportation
        __typename
      }
      __typename
    }
    countOfExceptions
    hasBlockingExceptions
    exceptions {
      allocationId
      exceptionCode
      expenseId
      isBlocking
      message
      parameters {
        entryExceptionAttendees {
          lastName
          firstName
          entryAmount
          crnCode
          totalExpensed
          totalAuthorized
          __typename
        }
        missingFields {
          missingSpecialParentField
          fields
          fieldIds
          __typename
        }
        __typename
      }
      parentExpenseId
      __typename
    }
    __typename
  }
  __typename
}

fragment ExpenseEntrySummaryFragment on ExpenseEntrySummary {
  allocationState
  approvedAmount {
    value
    currencyCode
    __typename
  }
  attendeeCount
  claimedAmount {
    value
    currencyCode
    __typename
  }
  eReceiptImageId
  expenseSourceIdentifiers {
    eReceiptId
    expenseCaptureImageId
    jptRouteId
    personalCardTransactionId
    quickExpenseId
    segmentId
    segmentTypeId
    tripId
    creditCardTransaction {
      id
      type
      __typename
    }
    __typename
  }
  expenseType {
    id
    code
    name
    meta {
      isJapanPublicTransportation
      __typename
    }
    __typename
  }
  id
  isImageRequired
  isPaperReceiptRequired
  isPersonalExpense
  jptRouteId
  location {
    city
    countryCode
    countrySubDivisionCode
    id
    name
    __typename
  }
  meta {
    canDelete
    hasAffidavit
    hasAllocation
    hasAttendees
    hasBlockingExceptions
    hasComments
    hasExceptions
    hasItemizations
    hasReceiptImage
    hasSource
    hasXmlReceipt
    hasSourceCreditCard
    hasSourceEReceipt
    hasSourceItinerary
    hasSourceExpenseIt
    hasSourceMobile
    hasSourcePersonalCard
    __typename
  }
  parentExpenseId
  paymentType {
    id
    code
    name
    __typename
  }
  receiptImageId
  rpeKey
  transactionAmount {
    value
    currencyCode
    __typename
  }
  postedAmount {
    value
    currencyCode
    __typename
  }
  transactionDate
  vendor {
    id
    description
    name
    __typename
  }
  __typename
}

fragment EreExpenseEntrySummaryFragment on ExpenseEntrySummary {
  ...ExpenseEntrySummaryFragment
  cctReceiptImageId
  travel {
    hotelCheckinDate
    hotelCheckoutDate
    __typename
  }
  itemizations {
    id
    attendeeCount
    allocationState
    isPersonalExpense
    approvedAmount {
      value
      currencyCode
      __typename
    }
    meta {
      canDelete
      hasAllocation
      hasAttendees
      hasComments
      hasExceptions
      hasBlockingExceptions
      __typename
    }
    expenseType {
      id
      code
      name
      __typename
    }
    rpeKey
    transactionAmount {
      value
      currencyCode
      __typename
    }
    transactionDate
    __typename
  }
  __typename
}

fragment AmountValueFragment on AmountValue {
  amountValue: value {
    value
    currencyCode
    __typename
  }
  __typename
}

fragment BooleanValueFragment on BooleanValue {
  booleanValue: value
  isValid
  __typename
}

fragment DateValueFragment on DateValue {
  dateValue: value
  isValid
  __typename
}

fragment ExchangeRateValueFragment on ExchangeRateValue {
  value
  operation
  __typename
}

fragment ExpenseAmountFragment on ExpenseAmount {
  expenseAmountValue: value
  __typename
}

fragment FloatValueFragment on FloatValue {
  floatValue: value
  __typename
}

fragment IntegerValueFragment on IntegerValue {
  integerValue: value
  __typename
}

fragment ListItemValueFragment on ListItemValue {
  code
  id
  listItemValue: value
  __typename
}

fragment ListValueFragment on ListValue {
  isValid
  listValue: value {
    code
    id
    value
    __typename
  }
  __typename
}

fragment LocationValueFragment on LocationListValue {
  isValid
  locationValue: value {
    id
    name
    city
    value
    countryCode
    countrySubDivisionCode
    __typename
  }
  __typename
}

fragment StringValueFragment on StringValue {
  stringValue: value
  __typename
}

fragment FormFieldFragment on FormField {
  id
  label
  formFieldId
  value {
    ...AmountValueFragment
    ...BooleanValueFragment
    ...DateValueFragment
    ...ExchangeRateValueFragment
    ...ExpenseAmountFragment
    ...FloatValueFragment
    ...IntegerValueFragment
    ...ListItemValueFragment
    ...ListValueFragment
    ...LocationValueFragment
    ...StringValueFragment
    __typename
  }
  accessMode
  control
  dataType
  defaultValue {
    value
    code
    listItemId
    isValid
    __typename
  }
  sequence
  maximumLength
  tooltip
  hasLineSeparator
  isCopyDownSource
  itemizationCopyDownAction
  isExternalList
  targetFieldSettings {
    action
    formFieldId
    lhsOperandSource
    operator
    rhsOperand
    __typename
  }
  comments {
    comment
    creationDate
    isLatest
    createdForUserId
    author {
      first
      last
      preferred
      __typename
    }
    __typename
  }
  options {
    id
    code
    value
    __typename
  }
  isRequired
  list {
    id
    level
    parentId
    displayFormat
    defaultSearchBy: searchCriteria
    __typename
  }
  dataValidator {
    validationExpression
    failureMessage
    __typename
  }
  requiredForSave
  taxAuthorityId
  taxFormId
  showFieldForCountryCode
  __typename
}

fragment JptRouteSummaryFragment on JptRouteSummary {
  assignment
  companyId
  creationDateTime
  currencyCode
  distanceUnit
  documentId
  entryId
  eReceiptId
  fromLocation
  hasCommuterPassDeduction
  hasIcCard
  id
  isCheap
  isEasy
  isFast
  isExpress
  isIcTicket
  isLegacyData
  isRoundTrip
  lastModifiedDateTime
  originType
  routeUUID
  seatType
  toLocation
  totalAdditionalAmount
  totalAmount
  totalDistance
  transactionDate
  transactionId
  userId
  __typename
}

fragment ExistingExpenseFormFragment on ExistingExpenseForm {
  expenseId
  expenseTypeId
  travelRequestEntries {
    entries {
      id
      value
      __typename
    }
    __typename
  }
  mainForm {
    attendeesLinkAccessMode
    calculateTaxLinkAccessMode
    fields {
      ...FormFieldFragment
      __typename
    }
    isFormEditable
    __typename
  }
  meta {
    canAllocate
    canDelete
    hasMixedAllocations
    hasXmlReceipt
    __typename
  }
  backendMileageConfigs
  expenseTypeDetails {
    expenseTypeId
    quickTips
    __typename
  }
  jptRouteSummary {
    ...JptRouteSummaryFragment
    __typename
  }
  __typename
}

fragment ExpenseTypeFragment on ExpenseType {
  id
  name
  itemizationType
  text
  header
  parentName
  code
  visibilityCode
  itemizeStyle
  shouldAddUserAsDefaultAttendee
  allowEditAttendeeAmount
  allowEditAttendeeCount
  shouldDisplayAttendeeAmounts
  itemizationWizardId
  meta {
    isTravelAllowanceExpense
    canCombineExpense
    isItemizationAllowed
    isItemizationRequired
    hasItemizationWizard
    isJapanPublicTransportation
    __typename
  }
  __typename
}

fragment ExpenseReportDetailsFragment on ExpenseReportDetails {
  id
  allocationFormId
  reportType
  userId
  policy {
    id
    allowReceiptAffidavits
    receiptAffidavitExplanation
    receiptAffidavitAcceptance
    expenseListDetailFormId
    meta {
      canShowReceipts
      canUploadImagesToExpenses
      __typename
    }
    __typename
  }
  expenseTypes {
    ...ExpenseTypeFragment
    __typename
  }
  meta {
    isApproved
    canReopen
    isReopened
    isSubmitted
    canAddExpense
    canAllocateExpenses
    isReceiptImageAvailable
    __typename
  }
  name
  claimedAmount {
    value
    currencyCode
    __typename
  }
  approvedAmount {
    value
    currencyCode
    __typename
  }
  reportTotal {
    value
    currencyCode
    __typename
  }
  currencyCode
  countryCode
  taxConfigId
  __typename
}
"""

# ==========================
# Read Cookies
# ==========================

def load_cookies(filename):
    cookies = {}

    with open(filename, "r", encoding="utf-8") as f:
        cookie_text = f.read().strip()

    for cookie in cookie_text.split(";"):
        if "=" in cookie:
            name, value = cookie.strip().split("=", 1)
            cookies[name] = value

    return cookies


session = requests.Session()
session.cookies.update(load_cookies(COOKIE_FILE))

# ==========================
# Upload Receipt
# ==========================

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Language": "en,en-US;q=0.9",
    "Priority": "u=4",
}

pdf_files = sorted(glob.glob(os.path.join(PDF_FOLDER, "*.pdf")))

if not pdf_files:
    print("No PDF files found.")
    exit()

for index, pdf_path in enumerate(pdf_files, start=1):

    print(f"\n[{index}/{len(pdf_files)}] Processing {os.path.basename(pdf_path)}")

    # ---------------------------------------------
    # Read values from PDF
    # ---------------------------------------------
    doc = pymupdf.open(pdf_path)

    number_plate = get_license_uber(doc)
    fare = get_fare_amount_uber(doc)
    transaction_date = get_date_uber(doc)

    doc.close()

    print(f"Date          : {transaction_date}")
    print(f"Fare          : {fare}")
    print(f"Number Plate  : {number_plate}")

    # ---------------------------------------------
    # Upload receipt
    # ---------------------------------------------
    with open(pdf_path, "rb") as pdf:

        upload = session.post(
            UPLOAD_URL,
            headers=headers,
            files={
                "file": (
                    os.path.basename(pdf_path),
                    pdf,
                    "application/pdf",
                )
            },
        )

    try:
        upload.raise_for_status()
    except Exception:
        print("Receipt upload failed.")
        print(upload.text)
        continue

    upload_json = upload.json()

    receipt_image_id = upload_json["imageId"]

    print(f"Receipt Image ID : {receipt_image_id}")
    time.sleep(DELAY_SECONDS)
    # ---------------------------------------------
    # Build GraphQL variables
    # ---------------------------------------------
    variables = {
        "taxFields": None,
        "shouldIncludeRpeKey": False,
        "userId": USER_ID,
        "contextRole": "TRAVELER",
        "isTrexEnabled": True,
        "reportId": REPORT_ID,
        "fields": {
            "expenseTypeId": "01102",
            "custom17": {
                "listItemId": "8A986A8C77C9DA43835822D9E7198CAA",
                "value": "8A986A8C77C9DA43835822D9E7198CAA",
            },
            "transactionDate": transaction_date,
            "businessPurpose": BUSINESS_PURPOSE,
            "vendorName": VENDOR_NAME,
            "locationId": "B40D3324AD004966804DDC2B2B160CCF",
            "paymentTypeId": "COPD",
            "transactionAmount": {
                "value": fare,
                "currencyCode": "INR",
            },
            "exchangeRate": {
                "operation": "MULTIPLY",
                "value": 1,
            },
            "taxRateLocation": "HOME",
            "receiptTypeId": "",
            "isExpensePartOfTravelAllowance": False,
            "comment": "",
            "custom1": {
                "value": number_plate,
            },
            "isPersonalExpense": False,
            "orgUnit1": {
                "value": "F3362811FBEBAA4495F3C72ED5BA15C4",
            },
            "orgUnit2": {
                "value": "084AAD620A5EFB429E759B6E4165E57B",
            },
            "orgUnit3": {
                "value": "46AEE5457FA8664F9B5CFB508CF8FDA6",
            },
            "receiptImageId": receipt_image_id,
        },
        "expenseTypeId": "01102",
        "policyId": "B94B849FD70E6F40BA689080712256F1",
        "expenseListDetailFormId": "A6BBECA62B9240258230320AE93D100D",
    }

    payload = {
        "operationName": "SaveNewExpenseEntry",
        "variables": variables,
        "query": GRAPHQL_MUTATION,
    }

    graphql_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Accept-Language": "en",
        "Content-Type": "application/json",
    }

    response = session.post(
        GRAPHQL_URL,
        headers=graphql_headers,
        json=payload,
    )

    print("Create Expense Status:", response.status_code)

    try:
        result = response.json()

        if "errors" in result:
            print("Expense creation failed.")
            print(json.dumps(result["errors"], indent=2))
        else:
            expense_id = result["data"]["createExpense"]["id"]
            print(f"Expense created successfully: {expense_id}")

    except Exception:
        print(response.text)

    # ---------------------------------------------
    # Delay before next file
    # ---------------------------------------------
    if index != len(pdf_files):
        print(f"Waiting {DELAY_SECONDS} seconds...")
        time.sleep(DELAY_SECONDS)